"""Laboratuvar deneyi: doğrudan uyarım, susturma ve kontrol karşılaştırması.

Bir deney en fazla iki koşul çalıştırır:
    kontrol    susturma uygulanmadan
    deney      seçilen nöronlar susturularak (çıkış sinapsları sıfırlanır; referans kodun yöntemi)

Susturma varsa iki koşul da **aynı tohumla** koşulur; böylece iki sonuç arasındaki fark yalnızca
susturmadan kaynaklanır. Davranış farkları deneme başına ateşleme hızlarıyla Welch t testinden
geçirilir (denemeler bağımsız, varyanslar eşit varsayılmaz).

Sonuçlar `sinek.decoder` ile aynı çözümleyiciden geçer; Laboratuvar ayrı bir "yorum" katmanı
kullanmaz.
"""

import time
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import torch
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field
from scipy import stats

from sinek.connectome.connectome import Connectome
from sinek.connectome.groups import Behavior, GroupRole
from sinek.connectome.pipeline import IndexBundle
from sinek.decoder.decoder import BehaviorCalibration, decode
from sinek.decoder.schema import (
    DecoderOutput,
    ModelInfo,
    SimulationMode,
    StimulusComponent,
    StimulusInfo,
)
from sinek.lab.selection import NeuronSelector, Selection, indices_of, resolve_selector
from sinek.simulation.lif import SimulationResult, Stimulus, simulate
from sinek.simulation.params import LIFParams
from sinek.simulation.scenarios import F_MAX_HZ

MAX_RATE_HZ = 400.0  # referans çalışmadaki en yüksek uyarım 260 Hz; üstü fizyolojik sayılmaz
MAX_STIMULI = 6
MAX_SILENCED = 6
SIGNIFICANCE_P = 0.05
# Bu oranın üzerinde susturma, modeli fizyolojik olmayan bir duruma sokabilir (yol haritası).
LARGE_SILENCING_SHARE = 0.05


class ProgressLike(Protocol):
    """İlerleme bildirimi: aşama etiketi + adım geri çağrısı (bkz. `sinek.lab.jobs`)."""

    def stage(self, step_tr: str, offset: float, span: float) -> None: ...

    def __call__(self, step: int, total: int) -> None: ...


class ExperimentError(ValueError):
    """Deney isteği geçersiz."""


class LabParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    n_trials: int = Field(default=30, ge=1, le=50)
    t_run_ms: float = Field(default=1000.0, ge=100.0, le=2000.0)
    seed: int = Field(default=0, ge=0, le=2**31 - 1)

    def to_lif(self) -> LIFParams:
        return LIFParams(n_trials=self.n_trials, t_run_ms=self.t_run_ms)


class LabStimulus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selector: NeuronSelector
    rate_hz: float = Field(gt=0, le=MAX_RATE_HZ)


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stimuli: list[LabStimulus] = Field(min_length=1, max_length=MAX_STIMULI)
    silenced: list[NeuronSelector] = Field(default_factory=list, max_length=MAX_SILENCED)
    params: LabParams = LabParams()


class BehaviorComparison(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    behavior: Behavior
    control_rate_hz: float
    silenced_rate_hz: float
    difference_hz: float
    percent_change: float | None  # kontrol sıfırsa tanımsız
    p_value: float
    significant: bool


class ConditionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label_tr: str
    output: DecoderOutput
    neuropil_rates_hz: dict[str, float]


class ExperimentResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stimuli: list[Selection]
    stimulus_rates_hz: list[float]
    silenced: list[Selection]
    silenced_neuron_count: int
    params: LabParams
    control: ConditionResult
    silenced_condition: ConditionResult | None
    comparisons: list[BehaviorComparison]
    warnings_tr: list[str]
    duration_seconds: float


@dataclass(frozen=True)
class _Condition:
    label: str
    result: SimulationResult
    readout_trial_rates: dict[Behavior, NDArray[np.float64]]


def _stimulus_info(selections: list[Selection], rates: list[float]) -> StimulusInfo:
    components = tuple(
        StimulusComponent(
            group=f"lab:{index}",
            name_tr=selection.label_tr,
            intensity=rate / F_MAX_HZ if rate <= F_MAX_HZ else None,
            rate_hz=rate,
            neuron_count=selection.size,
        )
        for index, (selection, rate) in enumerate(zip(selections, rates, strict=True))
    )
    key = "+".join(f"{s.label_tr}@{r:.0f}Hz" for s, r in zip(selections, rates, strict=True))
    return StimulusInfo(components=components, scenario_key=f"lab:{key}")


def _readout_trial_rates(
    result: SimulationResult, bundle: IndexBundle, params: LabParams
) -> dict[Behavior, NDArray[np.float64]]:
    """Davranış başına, deneme başına okuma hızı: en yüksek hızlı okuma nöronu üzerinden."""
    from sinek.decoder.decoder import readout_groups

    seconds = params.t_run_ms / 1000.0
    rates: dict[Behavior, NDArray[np.float64]] = {}
    for behavior, groups in readout_groups(bundle.groups).items():
        indices = np.concatenate([g.indices for g in groups]) if groups else np.empty(0, np.int64)
        if indices.size == 0:  # pragma: no cover - tanım dosyası her davranışı kapsar
            rates[behavior] = np.zeros(result.spike_counts.shape[0])
            continue
        per_trial = result.spike_counts[:, indices] / seconds  # (deneme, nöron)
        best = int(np.argmax(per_trial.mean(axis=0)))
        rates[behavior] = per_trial[:, best].astype(np.float64)
    return rates


def _decode_condition(
    condition: _Condition,
    bundle: IndexBundle,
    stimulus: StimulusInfo,
    params: LabParams,
    calibration: dict[Behavior, BehaviorCalibration],
) -> ConditionResult:
    result = condition.result
    rates = result.rates_hz
    model = ModelInfo(
        mode=SimulationMode.LIVE,
        n_trials=params.n_trials,
        t_run_ms=params.t_run_ms,
        seed=params.seed,
    )
    output = decode(
        rates,
        result.rates_std_hz,
        bundle.groups,
        stimulus,
        model,
        calibration,
        bundle.neuropils,
    )
    neuropil_rates: dict[str, float] = {}
    if bundle.neuropils is not None:
        neuropil_rates = {str(k): float(v) for k, v in bundle.neuropils.mean_rate(rates).items()}
    return ConditionResult(
        label_tr=condition.label, output=output, neuropil_rates_hz=neuropil_rates
    )


def _compare(control: _Condition, silenced: _Condition) -> list[BehaviorComparison]:
    comparisons = []
    for behavior, before in control.readout_trial_rates.items():
        after = silenced.readout_trial_rates[behavior]
        mean_before, mean_after = float(before.mean()), float(after.mean())
        if before.std() == 0 and after.std() == 0:
            p_value = 0.0 if mean_before != mean_after else 1.0
        else:
            p_value = float(stats.ttest_ind(before, after, equal_var=False).pvalue)
        comparisons.append(
            BehaviorComparison(
                behavior=behavior,
                control_rate_hz=mean_before,
                silenced_rate_hz=mean_after,
                difference_hz=mean_after - mean_before,
                percent_change=(
                    None if mean_before == 0 else 100 * (mean_after - mean_before) / mean_before
                ),
                p_value=p_value,
                significant=p_value < SIGNIFICANCE_P,
            )
        )
    return comparisons


def run_experiment(
    request: ExperimentRequest,
    bundle: IndexBundle,
    connectome: Connectome,
    calibration: dict[Behavior, BehaviorCalibration],
    device: torch.device | None = None,
    reporter: ProgressLike | None = None,
) -> ExperimentResult:
    """Deneyi çalıştırır: susturma varsa kontrol ve deney koşulları aynı tohumla koşulur."""
    started = time.monotonic()
    stimulus_selections = [resolve_selector(s.selector, bundle) for s in request.stimuli]
    rates = [s.rate_hz for s in request.stimuli]
    silenced_selections = [resolve_selector(s, bundle) for s in request.silenced]

    stimuli = [
        Stimulus(indices_of(selection, bundle), rate)
        for selection, rate in zip(stimulus_selections, rates, strict=True)
    ]
    silenced_indices = (
        np.unique(np.concatenate([indices_of(s, bundle) for s in silenced_selections]))
        if silenced_selections
        else np.empty(0, dtype=np.int64)
    )

    params = request.params
    lif = params.to_lif()

    def run(silence: NDArray[np.int64], label: str) -> _Condition:
        result = simulate(
            connectome,
            stimuli,
            params=lif,
            silenced=silence,
            seed=params.seed,
            device=device,
            progress=reporter,
        )
        return _Condition(label, result, _readout_trial_rates(result, bundle, params))

    stimulus = _stimulus_info(stimulus_selections, rates)
    span = 0.5 if silenced_indices.size else 1.0
    if reporter:
        reporter.stage("kontrol koşulu simüle ediliyor", 0.0, span)
    control = run(np.empty(0, dtype=np.int64), "kontrol")
    control_result = _decode_condition(control, bundle, stimulus, params, calibration)

    silenced_result = None
    comparisons: list[BehaviorComparison] = []
    if silenced_indices.size:
        if reporter:
            reporter.stage("susturma koşulu simüle ediliyor", 0.5, 0.5)
        experiment = run(silenced_indices, "susturma")
        silenced_result = _decode_condition(experiment, bundle, stimulus, params, calibration)
        comparisons = _compare(control, experiment)

    warnings_tr = []
    share = silenced_indices.size / connectome.n_neurons
    if share > LARGE_SILENCING_SHARE:
        warnings_tr.append(
            f"Nöronların %{100 * share:.1f}'i susturuldu. Geniş susturmalar modeli fizyolojik "
            "olmayan bir duruma sokabilir; sonuçlar model davranışı olarak yorumlanmalıdır."
        )
    readout_ids = {
        root_id
        for group in bundle.groups.values()
        if group.definition.role is GroupRole.READOUT
        for root_id in group.flywire_ids
    }
    silenced_readouts = readout_ids & {i for s in silenced_selections for i in s.flywire_ids}
    if silenced_readouts:
        warnings_tr.append(
            f"Susturulan {len(silenced_readouts)} nöron bir davranış okuma nöronudur. Susturma "
            "yalnızca nöronun çıkış bağlantılarını kapatır (referans yöntem); nöronun kendi "
            "ateşlemesi ölçülmeye devam eder, bu yüzden o davranışın okuması değişmeyebilir. "
            "Davranışı engellemek için ona girdi veren nöronları susturun."
        )
    for selection in [*stimulus_selections, *silenced_selections]:
        if selection.missing_ids:
            warnings_tr.append(
                f"{selection.label_tr}: {len(selection.missing_ids)} kimlik bu veri sürümünde yok."
            )

    return ExperimentResult(
        stimuli=stimulus_selections,
        stimulus_rates_hz=rates,
        silenced=silenced_selections,
        silenced_neuron_count=int(silenced_indices.size),
        params=params,
        control=control_result,
        silenced_condition=silenced_result,
        comparisons=comparisons,
        warnings_tr=warnings_tr,
        duration_seconds=round(time.monotonic() - started, 2),
    )
