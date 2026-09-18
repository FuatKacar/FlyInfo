"""Hazır senaryo paketinin gerçek veriyle denetimi (Faz 3 kabul ölçütleri).

1. Paketteki her senaryo çözümleyiciden geçer ve çıktı sözleşmesine uyar.
2. Aynı senaryo canlı simüle edildiğinde paketteki sonuçla **birebir** aynıdır (aynı tohum,
   aynı donanım türü). Ekran kartı gerekir; işlemcide tek senaryo ~8,5 dakika sürdüğü için
   ekran kartı yoksa atlanır.
"""

from functools import cache
from pathlib import Path

import numpy as np
import pytest
import torch

from sinek.chat.service import BrainService
from sinek.connectome.groups import Behavior
from sinek.connectome.pipeline import load_bundle, load_index_bundle
from sinek.decoder.decoder import load_calibration
from sinek.simulation.params import LIFParams
from sinek.simulation.precompute import PACKAGE_VERSION, run_scenario
from sinek.simulation.scenarios import make_scenario, scenario_set
from sinek.simulation.store import ScenarioPackage, ScenarioStore

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = ROOT / "artifacts" / "scenarios" / PACKAGE_VERSION

pytestmark = [
    pytest.mark.veri,
    pytest.mark.skipif(
        not (PACKAGE_DIR / "manifest.json").is_file(),
        reason="Hazır senaryo paketi yok (uv run sinek hesapla)",
    ),
]


@cache
def package() -> ScenarioPackage:
    return ScenarioPackage.open(PACKAGE_DIR)


def test_paket_tum_senaryolari_icerir() -> None:
    assert package().keys == {s.key for s in scenario_set()}


def test_tum_hazir_senaryolar_cozumleyici_sozlesmesine_uyar() -> None:
    brain = BrainService(
        load_index_bundle(ROOT / "data"), ScenarioStore(package(), None), load_calibration()
    )

    for scenario in scenario_set():
        view = brain.run(scenario)  # pydantic sözleşmesi burada doğrulanır
        output = view.output
        assert output.stimulus.scenario_key == scenario.key
        assert {b.behavior for b in output.behaviors} == set(Behavior)
        assert len(output.top_neuropils) <= 5
        assert output.model.n_trials == 30
        assert output.model.package_version == PACKAGE_VERSION
        assert len(view.neuropil_rates_hz) == 78, scenario.key
        if not scenario.components:
            assert output.active_neuron_count == 0  # kendiliğinden etkinlik yok


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Ekran kartı yok")
def test_canli_simulasyon_hazir_paketle_birebir_ayni() -> None:
    scenario = make_scenario(("sugar", 1.0))
    stored = package().load(scenario)

    live = run_scenario(scenario, load_bundle(ROOT / "data"), LIFParams())

    assert live.fingerprint == stored.fingerprint
    np.testing.assert_array_equal(live.indices, stored.indices)
    np.testing.assert_array_equal(live.count_sum, stored.count_sum)
    np.testing.assert_array_equal(live.count_sq, stored.count_sq)


def test_yayin_arsivi_koddaki_sabit_ozetle_ayni(tmp_path: Path) -> None:
    """Dağıtılan arşiv, bu paketten bayt bayt yeniden üretilebilir (hızlı deneme = tam üretim)."""
    from sinek.simulation.distribution import SCENARIO_ARCHIVE, build_archive, describe_archive

    arsiv = build_archive(PACKAGE_DIR, tmp_path / SCENARIO_ARCHIVE.filename)

    assert describe_archive(arsiv) == (SCENARIO_ARCHIVE.size, SCENARIO_ARCHIVE.sha256)
