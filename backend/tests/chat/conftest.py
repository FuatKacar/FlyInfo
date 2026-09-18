"""Sohbet hattı testleri için yapay beyin: gerçek veri gerektirmez.

Nöron kimlikleri 1–20. Uyarım grupları: sugar (1, 2), water (4), geosmin (3, yalnızca devre).
Her davranışın bir okuma nöronu vardır (10–14). Hazır paket: kontrol ve sugar@0.2.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

from sinek.chat.service import BrainService, ChatService
from sinek.connectome.connectome import NeuronIndex
from sinek.connectome.groups import Behavior, GroupDefinition, resolve_groups
from sinek.connectome.neuropils import NeuropilMap
from sinek.connectome.pipeline import IndexBundle
from sinek.decoder.decoder import BehaviorCalibration
from sinek.presentation.service import PresentationService
from sinek.simulation.params import LIFParams
from sinek.simulation.precompute import ScenarioResult, save_result, write_manifest
from sinek.simulation.scenarios import Scenario, make_scenario
from sinek.simulation.store import LiveSimulator, ScenarioPackage, ScenarioStore

READOUTS = {
    Behavior.FEEDING: ("mn9", 10),
    Behavior.ESCAPE: ("giant_fiber", 11),
    Behavior.ANTENNAL_GROOMING: ("adn1", 12),
    Behavior.BACKWARD_WALKING: ("mdn", 13),
    Behavior.FORWARD_WALKING: ("p9", 14),
}
SUGAR_LOW = make_scenario(("sugar", 0.2))
CONTROL = Scenario(())


def _definition(key: str, role: str, ids: list[int], **extra: object) -> GroupDefinition:
    return GroupDefinition.model_validate(
        {
            "key": key,
            "role": role,
            "name_tr": key,
            "description_tr": f"{key} grubu",
            "citations": [3],
            "selection": "annotation",
            "cell_types": [f"T{i}" for i in ids],
            **extra,
        }
    )


@pytest.fixture
def index_bundle() -> IndexBundle:
    ids = np.arange(1, 21, dtype=np.int64)
    annotations = pd.DataFrame(
        {
            "super_class": ["central"] * 20,
            "cell_class": [None] * 20,
            "cell_sub_class": [None] * 20,
            "cell_type": [f"T{i}" for i in ids],
            "hemibrain_type": [None] * 20,
            "side": ["left", "right"] * 10,
            "top_nt": ["acetylcholine"] * 19 + [None],
            "top_nt_conf": [0.9] * 19 + [np.nan],
        },
        index=pd.Index(ids, name="root_id"),
    )
    definitions = {
        "sugar": _definition("sugar", "stimulus", [1, 2]),
        "water": _definition("water", "stimulus", [4]),
        "geosmin": _definition("geosmin", "stimulus", [3], circuit_only=True),
    }
    for behavior, (key, neuron) in READOUTS.items():
        definitions[key] = _definition(key, "readout", [neuron], behavior=behavior.value)
    neurons = NeuronIndex(ids)
    # nöropil çıkış sinapsları: (model indeksi, nöropil, sayı)
    synapses = [(0, 1, 10), (9, 1, 5), (5, 1, 25), (9, 0, 5)]
    neuropils = NeuropilMap(
        names=("AL_L", "GNG"),
        counts=sp.coo_array(
            ([n for *_, n in synapses], ([i for i, *_ in synapses], [j for _, j, _ in synapses])),
            shape=(20, 2),
        ).tocsr(),
    )
    return IndexBundle(
        neurons, annotations, resolve_groups(definitions, neurons, annotations), neuropils
    )


def result(scenario: Scenario, spikes: dict[int, list[int]]) -> ScenarioResult:
    """spikes: model indeksi → deneme başına spike sayıları (30 deneme, 1 sn)."""
    indices = sorted(spikes)
    counts = [np.asarray(spikes[i], dtype=np.int64) for i in indices]
    return ScenarioResult(
        scenario=scenario,
        n_trials=30,
        t_run_ms=1000.0,
        indices=np.asarray(indices, dtype=np.int32),
        count_sum=np.asarray([c.sum() for c in counts], dtype=np.int64),
        count_sq=np.asarray([(c**2).sum() for c in counts], dtype=np.int64),
        fingerprint="test",
    )


# Şekerde beslenme okuma nöronu (indeks 9 = kimlik 10) ~40 Hz ateşler.
SUGAR_SPIKES = {0: [40] * 30, 1: [38] * 30, 9: [39, 41] * 15}
PARAMS = LIFParams(n_trials=30, t_run_ms=1000.0)


@pytest.fixture
def package(tmp_path: Path) -> ScenarioPackage:
    directory = tmp_path / "paket"
    directory.mkdir()
    save_result(directory / f"{CONTROL.key}.npz", result(CONTROL, {}))
    save_result(directory / f"{SUGAR_LOW.key}.npz", result(SUGAR_LOW, SUGAR_SPIKES))
    write_manifest(directory, (CONTROL, SUGAR_LOW), PARAMS, tmp_path)
    return ScenarioPackage.open(directory, PARAMS)


class FakeLive(LiveSimulator):
    """Canlı simülasyon yerine su senaryosunda beslenme nöronu ~20 Hz ateşler."""

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path, tmp_path)
        self.calls: list[str] = []

    def run(self, scenario: Scenario) -> ScenarioResult:
        self.calls.append(scenario.key)
        return result(scenario, {9: [20] * 30})


@pytest.fixture
def live(tmp_path: Path) -> FakeLive:
    return FakeLive(tmp_path)


@pytest.fixture
def brain(index_bundle: IndexBundle, package: ScenarioPackage, live: FakeLive) -> BrainService:
    calibration = {
        b: BehaviorCalibration(
            reference_rate_hz=80.0 if b is Behavior.FEEDING else None,
            reference_scenario="sugar@1.0" if b is Behavior.FEEDING else None,
            reference_group="mn9" if b is Behavior.FEEDING else None,
        )
        for b in Behavior
    }
    return BrainService(index_bundle, ScenarioStore(package, live), calibration)


@pytest.fixture
def chat(brain: BrainService) -> ChatService:
    return ChatService(brain, PresentationService([], None))
