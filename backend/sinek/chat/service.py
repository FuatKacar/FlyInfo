"""Katmanların birleştirildiği servisler.

    BrainService  senaryo → (hazır paket | canlı simülasyon) → çözümleyici çıktısı
    ChatService   Türkçe mesaj → sınıflandırıcı → senaryo → BrainService → sunum metni

Kapsam dışı mesajlarda kontrol (uyarımsız) senaryosu çözümlenir: arayüz yine gerçek bir
simülasyon sonucu gösterir ve sunum katmanı eşleşme olmadığını söyler.
"""

from dataclasses import dataclass
from pathlib import Path

from sinek.config import Settings
from sinek.connectome.groups import Behavior, GroupRole
from sinek.connectome.pipeline import IndexBundle, load_index_bundle
from sinek.decoder.decoder import BehaviorCalibration, decode, load_calibration
from sinek.decoder.schema import (
    DecoderOutput,
    ModelInfo,
    SimulationMode,
    StimulusComponent,
    StimulusInfo,
)
from sinek.lab.service import LabService
from sinek.presentation.providers import providers_from_settings
from sinek.presentation.service import Presentation, PresentationService
from sinek.simulation.precompute import PACKAGE_VERSION
from sinek.simulation.scenarios import Scenario
from sinek.simulation.store import (
    LiveSimulator,
    PackageError,
    ResultSource,
    ScenarioPackage,
    ScenarioStore,
)
from sinek.stimulus.classifier import Classification, classify
from sinek.stimulus.mapping import scenario_for_levels

_MODES = {
    ResultSource.PRECOMPUTED: SimulationMode.PRECOMPUTED,
    ResultSource.LIVE: SimulationMode.LIVE,
}


@dataclass(frozen=True)
class SimulationView:
    output: DecoderOutput
    # nöropil → sinaps ağırlıklı ortalama ateşleme hızı (Hz); beyin şeması için, LLM'e gönderilmez
    neuropil_rates_hz: dict[str, float]


class BrainService:
    def __init__(
        self,
        index: IndexBundle,
        store: ScenarioStore,
        calibration: dict[Behavior, BehaviorCalibration],
    ) -> None:
        self.index = index
        self.store = store
        self._calibration = calibration

    @property
    def stimulus_groups(self) -> tuple[str, ...]:
        return tuple(
            key for key, g in self.index.groups.items() if g.definition.role is GroupRole.STIMULUS
        )

    def run(self, scenario: Scenario) -> SimulationView:
        for group, _ in scenario.components:
            if group not in self.stimulus_groups:
                raise ValueError(f"Uyarım grubu değil: {group}")
        stored = self.store.get(scenario)
        result = stored.result
        n = self.index.neurons.n_neurons
        stimulus = StimulusInfo(
            components=tuple(
                StimulusComponent(
                    group=group,
                    name_tr=self.index.groups[group].definition.name_tr,
                    intensity=intensity,
                    rate_hz=rate,
                    neuron_count=self.index.groups[group].size,
                )
                for (group, intensity), (_, rate) in zip(
                    scenario.components, scenario.stimuli_hz, strict=True
                )
            ),
            scenario_key=scenario.key,
        )
        model = ModelInfo(
            mode=_MODES[stored.source],
            n_trials=result.n_trials,
            t_run_ms=result.t_run_ms,
            seed=stored.seed,
            package_version=stored.package_version,
        )
        rates = result.rates_hz(n)
        output = decode(
            rates,
            result.rates_std_hz(n),
            self.index.groups,
            stimulus,
            model,
            self._calibration,
            self.index.neuropils,
        )
        activity: dict[str, float] = {}
        if self.index.neuropils is not None:
            activity = {str(k): float(v) for k, v in self.index.neuropils.mean_rate(rates).items()}
        return SimulationView(output, activity)


@dataclass(frozen=True)
class ChatReply:
    classification: Classification
    simulation: SimulationView
    presentation: Presentation

    @property
    def output(self) -> DecoderOutput:
        return self.simulation.output


class ChatService:
    def __init__(self, brain: BrainService, presentation: PresentationService) -> None:
        self.brain = brain
        self._presentation = presentation

    def reply(self, message: str) -> ChatReply:
        classification = classify(message)
        simulation = self.brain.run(scenario_for_levels(classification.levels))
        return ChatReply(classification, simulation, self._presentation.present(simulation.output))


def package_dir(settings: Settings) -> Path:
    return settings.artifacts_dir / "scenarios" / PACKAGE_VERSION


@dataclass(frozen=True)
class Services:
    """Uygulamanın tüm servisleri. `package_problem`: hazır paket kullanılamıyorsa nedeni."""

    brain: BrainService
    chat: ChatService
    lab: LabService
    package_problem: str | None


def build_services(settings: Settings) -> Services:
    """Ayarlardan servisleri kurar."""
    index = load_index_bundle(settings.data_dir)
    package: ScenarioPackage | None
    package_problem: str | None = None
    try:
        package = ScenarioPackage.open(package_dir(settings))
    except PackageError as error:
        package, package_problem = None, str(error)
    store = ScenarioStore(package, LiveSimulator(settings.data_dir, settings.cache_dir))
    calibration = load_calibration()
    brain = BrainService(index, store, calibration)
    presentation = PresentationService(providers_from_settings(settings), settings.cache_dir)
    lab = LabService(index, settings.data_dir, settings.cache_dir, calibration)
    return Services(brain, ChatService(brain, presentation), lab, package_problem)
