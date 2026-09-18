import pytest

from sinek.connectome.groups import Behavior
from sinek.decoder.schema import (
    BehaviorReadout,
    DecoderOutput,
    ModelInfo,
    NeuropilActivity,
    SimulationMode,
    StimulusComponent,
    StimulusInfo,
)


def readout(
    behavior: Behavior, group: str, rate: float, score: float, active: bool
) -> BehaviorReadout:
    return BehaviorReadout(
        behavior=behavior,
        readout_group=group,
        rate_hz=rate,
        rate_std_hz=4.1,
        score=score,
        active=active,
    )


@pytest.fixture
def sugar_output() -> DecoderOutput:
    return DecoderOutput(
        stimulus=StimulusInfo(
            components=(
                StimulusComponent(
                    group="sugar",
                    name_tr="Şekere duyarlı tat nöronları",
                    intensity=0.8,
                    rate_hz=160,
                    neuron_count=21,
                ),
            ),
            match_score=0.91,
            scenario_key="sugar@0.8",
        ),
        behaviors=(
            readout(Behavior.FEEDING, "mn9", 38.24, 0.82, True),
            readout(Behavior.ESCAPE, "giant_fiber", 0.0, 0.0, False),
            readout(Behavior.ANTENNAL_GROOMING, "adn1", 0.0, 0.0, False),
            readout(Behavior.BACKWARD_WALKING, "mdn", 0.0, 0.0, False),
            readout(Behavior.FORWARD_WALKING, "p9", 0.0, 0.0, False),
        ),
        circuit_only=False,
        top_neuropils=(
            NeuropilActivity(neuropil="GNG", events_hz=34340429.0, share=0.62),
            NeuropilActivity(neuropil="PRW", events_hz=3730892.0, share=0.07),
        ),
        active_neuron_count=392,
        model=ModelInfo(mode=SimulationMode.PRECOMPUTED, n_trials=30, t_run_ms=1000, seed=7),
    )
