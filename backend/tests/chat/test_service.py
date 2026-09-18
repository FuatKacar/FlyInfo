import json
from pathlib import Path

import pytest

from sinek.chat.service import BrainService, ChatService
from sinek.connectome.groups import Behavior, load_group_definitions
from sinek.decoder.schema import DecoderOutput, SimulationMode
from sinek.simulation.params import LIFParams
from sinek.simulation.precompute import save_result
from sinek.simulation.scenarios import make_scenario
from sinek.simulation.store import (
    LiveSimulator,
    PackageError,
    ScenarioPackage,
    ScenarioStore,
    live_cache_name,
)
from sinek.stimulus.mapping import scenario_for_levels
from tests.chat.conftest import PARAMS, SUGAR_LOW, FakeLive, result


def feeding(output: DecoderOutput) -> tuple[float, float | None, bool]:
    (item,) = [b for b in output.behaviors if b.behavior is Behavior.FEEDING]
    return item.rate_hz, item.score, item.active


# --- Sınıflandırıcı düzeyi → senaryo ---------------------------------------------------------


@pytest.mark.parametrize(
    ("levels", "key"),
    [
        ({}, "kontrol"),
        ({"sugar": 1}, "sugar@0.2"),
        ({"sugar": 2, "water": 2}, "sugar@0.6+water@0.6"),
        ({"looming": 3, "bitter": 1}, "bitter@0.2+looming@1.0"),
    ],
)
def test_duzeyler_hazir_izgaraya_eslenir(levels: dict[str, int], key: str) -> None:
    assert scenario_for_levels(levels).key == key


def test_gecersiz_duzey_reddedilir() -> None:
    with pytest.raises(ValueError, match="düzey"):
        scenario_for_levels({"sugar": 4})


def test_anahtarda_kaybolacak_yogunluk_reddedilir() -> None:
    with pytest.raises(ValueError, match="0,1"):
        make_scenario(("sugar", 0.35))


# --- Hazır paket bütünlüğü --------------------------------------------------------------------


def test_paket_dosyasi_degisirse_kullanilmaz(package: ScenarioPackage) -> None:
    save_result(package.directory / f"{SUGAR_LOW.key}.npz", result(SUGAR_LOW, {9: [99] * 30}))

    with pytest.raises(PackageError, match="bozuk"):
        package.load(SUGAR_LOW)


def test_manifest_yoksa_paket_acilmaz(tmp_path: Path) -> None:
    with pytest.raises(PackageError, match="Manifest yok"):
        ScenarioPackage.open(tmp_path)


def test_grup_tanimi_degismisse_paket_acilmaz(package: ScenarioPackage) -> None:
    definitions = load_group_definitions()
    key, group = next(iter(definitions.items()))
    definitions[key] = group.model_copy(update={"ids": (*group.ids, 424242)})

    with pytest.raises(PackageError, match="grubu"):
        ScenarioPackage.open(package.directory, PARAMS, definitions)


def test_yalnizca_yorum_degisirse_paket_gecerli_kalir(package: ScenarioPackage) -> None:
    """Bütünlük denetimi dosyanın ham hâlini değil, ayrıştırılmış tanımları özetler."""
    acik = ScenarioPackage.open(package.directory, PARAMS, load_group_definitions())

    assert acik.keys == package.keys


def test_farkli_parametreyle_uretilen_paket_acilmaz(package: ScenarioPackage) -> None:
    with pytest.raises(PackageError, match="parametre"):
        ScenarioPackage.open(package.directory, LIFParams(n_trials=10))


def test_farkli_kaynak_ozetiyle_uretilen_paket_acilmaz(package: ScenarioPackage) -> None:
    path = package.directory / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["sources"] = {"Completeness_783.csv": "0" * 64}
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PackageError, match="kaynak"):
        ScenarioPackage.open(package.directory, PARAMS)


# --- Sonuç kaynağı: hazır → canlı ------------------------------------------------------------


def test_hazir_senaryo_paketten_eksik_senaryo_canli(brain: BrainService, live: FakeLive) -> None:
    precomputed = brain.run(SUGAR_LOW).output
    computed = brain.run(make_scenario(("water", 0.6))).output

    assert precomputed.model.mode is SimulationMode.PRECOMPUTED
    assert precomputed.model.package_version == "1"
    assert computed.model.mode is SimulationMode.LIVE
    assert computed.model.package_version is None
    assert live.calls == ["water@0.6"]


def test_canli_kapaliysa_eksik_senaryo_hata_verir(package: ScenarioPackage) -> None:
    with pytest.raises(PackageError, match="canlı"):
        ScenarioStore(package, None).get(make_scenario(("water", 0.6)))


def test_canli_sonuc_onbellege_yazilir_ve_tekrar_hesaplanmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def fake_run(scenario: object, _bundle: object, _params: object) -> object:
        calls.append(str(scenario))
        return result(SUGAR_LOW, {9: [5] * 30})

    monkeypatch.setattr("sinek.simulation.store.load_bundle", lambda _d: object())
    monkeypatch.setattr("sinek.simulation.store.run_scenario", fake_run)
    simulator = LiveSimulator(tmp_path, tmp_path)

    first = simulator.run(SUGAR_LOW)
    second = LiveSimulator(tmp_path, tmp_path).run(SUGAR_LOW)

    assert len(calls) == 1
    assert first.count_sum.tolist() == second.count_sum.tolist()
    assert list((tmp_path / "scenarios").glob("*.tmp.npz")) == []


def test_canli_onbellek_adi_girdilerle_degisir() -> None:
    base = live_cache_name(SUGAR_LOW, PARAMS)
    definitions = load_group_definitions()
    key, group = next(iter(definitions.items()))
    definitions[key] = group.model_copy(update={"ids": (*group.ids, 424242)})

    assert base.startswith("sugar@0.2-")
    assert live_cache_name(SUGAR_LOW, LIFParams(n_trials=29)) != base
    assert live_cache_name(SUGAR_LOW, PARAMS, definitions) != base


# --- Çözümleme ve sohbet ----------------------------------------------------------------------


def test_cozumleyici_ciktisi_uyarim_ve_model_bilgisini_tasir(brain: BrainService) -> None:
    output = brain.run(SUGAR_LOW).output
    (component,) = output.stimulus.components

    assert (component.group, component.intensity, component.rate_hz) == ("sugar", 0.2, 40.0)
    assert component.neuron_count == 2
    assert feeding(output) == (40.0, 0.5, True)
    assert output.active_neuron_count == 3
    assert output.model.n_trials == 30


def test_noropil_ortalama_hizi_sinaps_agirlikli(brain: BrainService) -> None:
    rates = brain.run(SUGAR_LOW).neuropil_rates_hz

    # GNG: nöron 0 (40 Hz, 10 sinaps) + nöron 9 (40 Hz, 5 sinaps) + nöron 5 (0 Hz, 25 sinaps)
    assert rates["GNG"] == pytest.approx((40 * 10 + 40 * 5) / 40)
    assert rates["AL_L"] == pytest.approx(40.0)  # yalnızca nöron 9
    assert set(rates) == {"AL_L", "GNG"}
    assert brain.run(make_scenario()).neuropil_rates_hz == {"AL_L": 0.0, "GNG": 0.0}


def test_okuma_grubu_uyarilamaz(brain: BrainService) -> None:
    with pytest.raises(ValueError, match="Uyarım grubu değil"):
        brain.run(make_scenario(("mn9", 1.0)))


def test_sohbet_mesaji_senaryoya_ve_metne_donusur(chat: ChatService) -> None:
    reply = chat.reply("Sana biraz bal getirdim")

    assert reply.classification.levels == {"sugar": 1}
    assert reply.output.stimulus.scenario_key == "sugar@0.2"
    assert reply.presentation.source == "template"
    assert "40" in reply.presentation.text


def test_kapsam_disi_mesaj_kontrol_senaryosunu_cozumler(chat: ChatService) -> None:
    reply = chat.reply("Kuru fasulye")

    assert not reply.classification.in_scope
    assert reply.output.stimulus.scenario_key == "kontrol"
    assert reply.output.stimulus.components == ()
    assert reply.output.active_behaviors == ()
