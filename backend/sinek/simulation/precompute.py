"""Senaryo setinin toplu simülasyonu ve sürümlü veri paketi.

Her senaryo için yalnızca en az bir spike atan nöronlar saklanır:
    indices     int32  model indeksi
    count_sum   int64  denemeler boyunca toplam spike sayısı
    count_sq    int64  deneme başına spike sayılarının karelerinin toplamı
Ortalama hız ve standart sapma bu tam sayılardan kayıpsız hesaplanır (bkz. `ScenarioResult`).

Paket dizini:
    artifacts/scenarios/<paket_surumu>/
        manifest.json          kaynak özetleri, parametreler, yazılım/donanım, senaryo özetleri
        <senaryo_anahtari>.npz
"""

import hashlib
import json
import platform
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray

from sinek import __version__
from sinek.connectome.download import sha256_of
from sinek.connectome.groups import DEFAULT_GROUPS_PATH, ResolvedGroup, definitions_digest
from sinek.connectome.pipeline import DataBundle, raw_dir
from sinek.connectome.sources import SOURCES
from sinek.simulation.lif import Stimulus, simulate
from sinek.simulation.params import LIFParams
from sinek.simulation.scenarios import F_MAX_HZ, Scenario

PACKAGE_VERSION = "1"
SCHEMA_VERSION = 1

ProgressCallback = Callable[[int, int, Scenario, str], None]


def scenario_seed(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], "little")


def scenario_fingerprint(scenario: Scenario, bundle: DataBundle, params: LIFParams) -> str:
    """Sonucu belirleyen tüm girdilerin özeti: parametreler, senaryo, uyarılan kimlikler, işaret."""
    stimulated = {
        group: sorted(int(i) for i in bundle.groups[group].flywire_ids)
        for group, _ in scenario.components
    }
    payload = {
        "params": params.to_dict(),
        "scenario": scenario.key,
        "f_max_hz": F_MAX_HZ,
        "stimulated": stimulated,
        "sign_source": bundle.connectome.sign_source.value,
        "n_neurons": bundle.connectome.n_neurons,
        "n_synapses": bundle.connectome.n_synapses,
        "seed": scenario_seed(scenario.key),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _file_name(scenario: Scenario) -> str:
    # Windows dosya adlarında '@' ve '+' güvenlidir; '.' yoğunluk içindir.
    return f"{scenario.key}.npz"


@dataclass(frozen=True)
class ScenarioResult:
    scenario: Scenario
    n_trials: int
    t_run_ms: float
    indices: NDArray[np.int32]
    count_sum: NDArray[np.int64]
    count_sq: NDArray[np.int64]
    fingerprint: str

    def rates_hz(self, n_neurons: int) -> NDArray[np.float64]:
        rates = np.zeros(n_neurons)
        rates[self.indices] = self.count_sum / self.n_trials / (self.t_run_ms / 1000.0)
        return rates

    def rates_std_hz(self, n_neurons: int) -> NDArray[np.float64]:
        mean = self.count_sum / self.n_trials
        variance = np.maximum(self.count_sq / self.n_trials - mean**2, 0.0)  # ddof = 0
        std = np.zeros(n_neurons)
        std[self.indices] = np.sqrt(variance) / (self.t_run_ms / 1000.0)
        return std


def save_result(path: Path, result: ScenarioResult) -> None:
    np.savez_compressed(
        path,
        indices=result.indices,
        count_sum=result.count_sum,
        count_sq=result.count_sq,
        n_trials=np.int64(result.n_trials),
        t_run_ms=np.float64(result.t_run_ms),
        fingerprint=np.array(result.fingerprint),
    )


def load_result(path: Path, scenario: Scenario) -> ScenarioResult:
    with np.load(path) as data:
        return ScenarioResult(
            scenario=scenario,
            n_trials=int(data["n_trials"]),
            t_run_ms=float(data["t_run_ms"]),
            indices=data["indices"],
            count_sum=data["count_sum"],
            count_sq=data["count_sq"],
            fingerprint=str(data["fingerprint"]),
        )


def run_scenario(
    scenario: Scenario, bundle: DataBundle, params: LIFParams, device: torch.device | None = None
) -> ScenarioResult:
    groups: dict[str, ResolvedGroup] = bundle.groups
    stimuli = [Stimulus(groups[group].indices, rate) for group, rate in scenario.stimuli_hz]
    result = simulate(
        bundle.connectome, stimuli, params=params, seed=scenario_seed(scenario.key), device=device
    )
    counts = result.spike_counts.astype(np.int64)  # (deneme, nöron)
    total = counts.sum(axis=0)
    active = np.flatnonzero(total).astype(np.int32)
    return ScenarioResult(
        scenario=scenario,
        n_trials=params.n_trials,
        t_run_ms=params.t_run_ms,
        indices=active,
        count_sum=total[active],
        count_sq=(counts[:, active] ** 2).sum(axis=0),
        fingerprint=scenario_fingerprint(scenario, bundle, params),
    )


def environment() -> dict[str, str]:
    device = (
        torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else platform.processor() or "cpu"
    )
    return {
        "sinek": __version__,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "device": device,
    }


def write_manifest(
    package_dir: Path,
    scenarios: tuple[Scenario, ...],
    params: LIFParams,
    data_dir: Path,
) -> Path:
    raw = raw_dir(data_dir)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_version": PACKAGE_VERSION,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": "FlyWire v783",
        "sources": {s.filename: s.sha256 for s in SOURCES if (raw / s.filename).is_file()},
        "neuron_groups_sha256": sha256_of(DEFAULT_GROUPS_PATH),  # bilgi amaçlı (yorumlar dahil)
        "neuron_groups_definitions_sha256": definitions_digest(),  # bütünlük denetimi
        "sign_source": "reference",
        "params": params.to_dict(),
        "f_max_hz": F_MAX_HZ,
        "seed_rule": "sha256(senaryo_anahtari)[:4], little-endian",
        "environment": environment(),
        "scenarios": {
            s.key: {
                "components": [[g, i] for g, i in s.components],
                "file": _file_name(s),
                "sha256": sha256_of(package_dir / _file_name(s)),
            }
            for s in scenarios
        },
    }
    path = package_dir / "manifest.json"
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    return path


def precompute(
    scenarios: tuple[Scenario, ...],
    bundle: DataBundle,
    package_dir: Path,
    data_dir: Path,
    params: LIFParams | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    """Eksik senaryoları hesaplar (kaldığı yerden devam eder) ve manifesti yazar."""
    params = params or LIFParams()
    package_dir.mkdir(parents=True, exist_ok=True)
    for number, scenario in enumerate(scenarios, start=1):
        path = package_dir / _file_name(scenario)
        expected = scenario_fingerprint(scenario, bundle, params)
        if path.is_file() and load_result(path, scenario).fingerprint == expected:
            if progress:
                progress(number, len(scenarios), scenario, "mevcut")
            continue
        if progress:
            progress(number, len(scenarios), scenario, "basliyor")
        result = run_scenario(scenario, bundle, params)
        partial = path.with_suffix(".tmp.npz")
        save_result(partial, result)
        partial.replace(path)
        if progress:
            progress(number, len(scenarios), scenario, "hesaplandi")
    return write_manifest(package_dir, scenarios, params, data_dir)
