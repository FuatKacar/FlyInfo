"""Doğrulama deneylerini çalıştırır, sonuçları önbelleğe alır ve referansla karşılaştırır.

İki veri kümesi desteklenir:
    v630: makalenin verisi ve makale kodundaki kimlikler → modelin doğrulaması
    v783: uygulamanın verisi ve `neuron_groups.toml` grupları (CAVE ile doğrulanmış ardıl
          kimliklerle) → uygulamanın makale sonuçlarını koruduğunun gösterilmesi
          (tüm beyin karşılaştırması yalnızca iki sürümde ortak kimlikli nöronlarla)
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from sinek.connectome.connectome import Connectome, build_connectome
from sinek.connectome.download import download_all
from sinek.connectome.groups import load_group_definitions
from sinek.connectome.pipeline import load_bundle, raw_dir
from sinek.simulation.lif import Stimulus, simulate
from sinek.simulation.params import LIFParams
from sinek.validation.compare import (
    SingleNeuronComparison,
    WholeBrainComparison,
    compare_single,
    compare_whole_brain,
)
from sinek.validation.experiments import (
    EXPERIMENTS,
    V783_SILENCING_SUCCESSORS,
    ReferenceExperiment,
)
from sinek.validation.sources import (
    V630_COMPLETENESS,
    V630_CONNECTIVITY,
    V630_SOURCES,
    fetch_reference_tables,
    reference_dir,
)

Dataset = Literal["v630", "v783"]
ExperimentStatus = Literal["basliyor", "hesaplandi", "onbellekten", "atlandi"]
ExperimentCallback = Callable[[int, int, ReferenceExperiment, ExperimentStatus], None]


@dataclass(frozen=True)
class ExperimentOutcome:
    experiment: ReferenceExperiment
    dataset: Dataset
    rates_hz: NDArray[np.float64]
    rates_std_hz: NDArray[np.float64]
    comparison: WholeBrainComparison | SingleNeuronComparison
    reference_rates_hz: NDArray[np.float64] | None  # yalnızca tüm beyin deneylerinde
    comparable: NDArray[np.bool_] | None  # karşılaştırılabilir nöronlar (v783: ortak kimlikler)
    stimulus_sizes: dict[str, int]  # grup anahtarı → uyarılan nöron sayısı


@dataclass(frozen=True)
class _Context:
    dataset: Dataset
    connectome: Connectome
    stimulus_groups: dict[str, NDArray[np.int64]]
    comparable: NDArray[np.bool_] | None


def experiment_seed(key: str) -> int:
    """Deney anahtarından kararlı tohum (tekrarlanabilirlik)."""
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "little")


def load_v630(data_dir: Path) -> Connectome:
    download_all(raw_dir(data_dir), V630_SOURCES)
    raw = raw_dir(data_dir)
    return build_connectome(raw / V630_COMPLETENESS.filename, raw / V630_CONNECTIVITY.filename)


def _context(dataset: Dataset, data_dir: Path) -> _Context:
    v630 = load_v630(data_dir)
    stimulus_keys = {key for e in EXPERIMENTS for key, _ in e.stimuli}
    if dataset == "v630":
        definitions = load_group_definitions()
        groups = {}
        for key in stimulus_keys:
            indices, missing = v630.index_of(list(definitions[key].ids))
            if missing:
                raise RuntimeError(f"{key}: v630'da bulunamayan referans kimlikleri {missing}")
            groups[key] = indices
        return _Context(dataset, v630, groups, None)

    bundle = load_bundle(data_dir)
    connectome = bundle.connectome
    comparable = np.isin(connectome.flywire_ids, v630.flywire_ids)
    groups = {key: bundle.groups[key].indices for key in stimulus_keys}
    return _Context(dataset, connectome, groups, comparable)


def _cache_path(
    cache_dir: Path, experiment: ReferenceExperiment, params: LIFParams, context: _Context
) -> Path:
    """Önbellek anahtarı; parametreler, deney tanımı ve uyarılan nöronların kimlikleri.

    Grup bileşimi değişirse (ör. yeni ardıl kimlik) eski sonuç kullanılmaz.
    """
    stimulated = {
        key: sorted(int(i) for i in context.connectome.flywire_ids[context.stimulus_groups[key]])
        for key, _ in experiment.stimuli
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            {"params": params.to_dict(), "exp": repr(experiment), "stimulated": stimulated},
            sort_keys=True,
        ).encode()
    ).hexdigest()[:12]
    return cache_dir / f"{experiment.key}-{fingerprint}.npz"


def _run_or_load(
    experiment: ReferenceExperiment,
    context: _Context,
    params: LIFParams,
    cache_dir: Path,
    silenced: NDArray[np.int64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], bool]:
    path = _cache_path(cache_dir, experiment, params, context)
    if path.is_file():
        cached = np.load(path)
        return cached["rates"], cached["std"], True
    stimuli = [Stimulus(context.stimulus_groups[key], rate) for key, rate in experiment.stimuli]
    result = simulate(
        context.connectome,
        stimuli,
        params=params,
        silenced=silenced,
        seed=experiment_seed(experiment.key),
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, rates=result.rates_hz, std=result.rates_std_hz)
    return result.rates_hz, result.rates_std_hz, False


def _reference_whole_brain(
    experiment: ReferenceExperiment, connectome: Connectome, data_dir: Path, strict: bool
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    base = reference_dir(data_dir)
    rates = pd.read_csv(base / experiment.table, index_col=0)[experiment.column]
    stds = pd.read_csv(base / experiment.std_table, index_col=0)[experiment.column]
    ids = rates.index.to_numpy(dtype=np.int64)
    indices, missing = connectome.index_of(ids)
    if missing and strict:
        raise RuntimeError(f"{experiment.key}: referans tablodaki {len(missing)} nöron veride yok")
    present = ~np.isin(ids, missing)
    mean = np.zeros(connectome.n_neurons)
    std = np.zeros(connectome.n_neurons)
    mean[indices] = rates.to_numpy(dtype=np.float64)[present]
    std[indices] = stds.to_numpy(dtype=np.float64)[present]
    return mean, std


def _reference_single(experiment: ReferenceExperiment, data_dir: Path) -> tuple[float, float]:
    base = reference_dir(data_dir)
    # Sütun başlığı bazı tablolarda bilimsel gösterimle yazılmış kimliktir; konumla okunur.
    rates = pd.read_csv(base / experiment.table, index_col=0).iloc[:, 0]
    stds = pd.read_csv(base / experiment.std_table, index_col=0).iloc[:, 0]
    return float(rates[experiment.column]), float(stds[experiment.column])


def run_validation(
    data_dir: Path,
    cache_dir: Path,
    params: LIFParams | None = None,
    on_experiment: ExperimentCallback | None = None,
    dataset: Dataset = "v630",
) -> list[ExperimentOutcome]:
    params = params or LIFParams()
    fetch_reference_tables(data_dir)
    context = _context(dataset, data_dir)
    connectome = context.connectome
    total = len(EXPERIMENTS)

    outcomes = []
    for number, experiment in enumerate(EXPERIMENTS, start=1):
        silenced_ids = list(experiment.silenced_ids)
        if dataset == "v783":
            silenced_ids = [V783_SILENCING_SUCCESSORS.get(i, i) for i in silenced_ids]
        silenced, missing_silenced = connectome.index_of(silenced_ids)
        readout: NDArray[np.int64] | None = None
        if experiment.readout_id is not None:
            readout, _ = connectome.index_of([experiment.readout_id])
        if missing_silenced or (readout is not None and readout.size == 0):
            if dataset == "v630":
                raise RuntimeError(f"{experiment.key}: gerekli nöron v630'da yok")
            if on_experiment:
                on_experiment(number, total, experiment, "atlandi")
            continue

        if on_experiment:
            on_experiment(number, total, experiment, "basliyor")
        rates, std, cached = _run_or_load(experiment, context, params, cache_dir, silenced)
        if on_experiment:
            on_experiment(number, total, experiment, "onbellekten" if cached else "hesaplandi")

        comparison: WholeBrainComparison | SingleNeuronComparison
        reference_rates = None
        if experiment.kind == "whole_brain":
            reference_rates, reference_std = _reference_whole_brain(
                experiment, connectome, data_dir, strict=dataset == "v630"
            )
            comparison = compare_whole_brain(
                rates, std, reference_rates, reference_std, params.n_trials, context.comparable
            )
        else:
            assert readout is not None
            index = int(readout[0])
            ref_mean, ref_std = _reference_single(experiment, data_dir)
            comparison = compare_single(
                float(rates[index]), float(std[index]), ref_mean, ref_std, params.n_trials
            )
        outcomes.append(
            ExperimentOutcome(
                experiment=experiment,
                dataset=dataset,
                rates_hz=rates,
                rates_std_hz=std,
                comparison=comparison,
                reference_rates_hz=reference_rates,
                comparable=context.comparable,
                stimulus_sizes={
                    k: int(context.stimulus_groups[k].size) for k, _ in experiment.stimuli
                },
            )
        )
    return outcomes
