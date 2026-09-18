from functools import cache
from pathlib import Path

import pytest

from sinek.connectome.groups import Behavior
from sinek.connectome.pipeline import DataBundle, load_bundle, raw_dir
from sinek.connectome.sources import SOURCES
from sinek.decoder.decoder import (
    BehaviorCalibration,
    decode,
    is_active,
    load_calibration,
)
from sinek.decoder.schema import (
    DecoderOutput,
    ModelInfo,
    SimulationMode,
    StimulusComponent,
    StimulusInfo,
)
from sinek.simulation.precompute import load_result
from sinek.simulation.scenarios import F_MAX_HZ, make_scenario

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "artifacts" / "scenarios" / "1"


@pytest.mark.parametrize(
    ("rate", "std", "expected"),
    [
        (4.9, 0.0, False),  # eşik altı
        (5.0, 0.0, True),
        (30.0, 5.0, True),
        (6.0, 60.0, False),  # çok gürültülü: sıfırdan ayırt edilemez
    ],
)
def test_etkinlik_esigi(rate: float, std: float, expected: bool) -> None:
    assert is_active(rate, std, n_trials=30) is expected


def test_kalibrasyon_dosyasi_tum_davranislari_icerir() -> None:
    calibration = load_calibration()

    assert set(calibration) == set(Behavior)
    for behavior, entry in calibration.items():
        if entry.reference_rate_hz is None:
            assert entry.reference_scenario is None, behavior
        else:
            assert entry.reference_rate_hz > 0


# --- Gerçek veri ve hazır senaryo paketi ile bilimsel testler --------------------------------

requires_data = pytest.mark.skipif(
    not all((raw_dir(ROOT / "data") / s.filename).is_file() for s in SOURCES),
    reason="FlyWire verisi indirilmemiş (uv run sinek indir)",
)


@cache
def bundle() -> DataBundle:
    return load_bundle(ROOT / "data")


def decode_scenario(*components: tuple[str, float]) -> DecoderOutput:
    scenario = make_scenario(*components)
    path = PACKAGE / f"{scenario.key}.npz"
    if not path.is_file():
        pytest.skip(f"hazır senaryo yok: {scenario.key} (uv run sinek hesapla)")
    b = bundle()
    n = b.connectome.n_neurons
    result = load_result(path, scenario)
    stimulus = StimulusInfo(
        components=tuple(
            StimulusComponent(
                group=g,
                name_tr=b.groups[g].definition.name_tr,
                intensity=i,
                rate_hz=i * F_MAX_HZ,
                neuron_count=b.groups[g].size,
            )
            for g, i in scenario.components
        ),
        scenario_key=scenario.key,
    )
    model = ModelInfo(
        mode=SimulationMode.PRECOMPUTED,
        n_trials=result.n_trials,
        t_run_ms=result.t_run_ms,
        seed=0,
        package_version="1",
    )
    return decode(
        result.rates_hz(n),
        result.rates_std_hz(n),
        b.groups,
        stimulus,
        model,
        load_calibration(),
        b.neuropils,
    )


def active(output: DecoderOutput) -> set[Behavior]:
    return {b.behavior for b in output.active_behaviors}


def readout(output: DecoderOutput, behavior: Behavior) -> float:
    (item,) = [b for b in output.behaviors if b.behavior is behavior]
    return item.rate_hz


@pytest.mark.veri
@requires_data
def test_kontrolde_hicbir_davranis_yok() -> None:
    output = decode_scenario()

    assert active(output) == set()
    assert output.active_neuron_count == 0
    assert output.top_neuropils == ()


@pytest.mark.veri
@requires_data
def test_seker_doza_bagli_beslenme() -> None:
    weak, strong = decode_scenario(("sugar", 0.2)), decode_scenario(("sugar", 1.0))

    assert Behavior.FEEDING not in active(weak)
    assert active(strong) == {Behavior.FEEDING}  # Shiu et al. 2024, şekil 1
    assert strong.top_neuropils[0].neuropil == "GNG"


@pytest.mark.veri
@requires_data
def test_aci_sekerin_beslenme_yanitini_baskilar() -> None:
    sugar = readout(decode_scenario(("sugar", 1.0)), Behavior.FEEDING)
    mixed = readout(decode_scenario(("sugar", 1.0), ("bitter", 1.0)), Behavior.FEEDING)

    assert active(decode_scenario(("bitter", 1.0))) == set()
    assert mixed < 0.25 * sugar  # Shiu et al. 2024, şekil 3A


@pytest.mark.veri
@requires_data
def test_johnston_organi_anten_temizleme() -> None:
    output = decode_scenario(("johnston_organ", 0.8))

    assert active(output) == {Behavior.ANTENNAL_GROOMING}  # Hampel et al. 2015


@pytest.mark.veri
@requires_data
def test_tehdit_kacis_ve_geri_yurume() -> None:
    output = decode_scenario(("looming", 1.0))

    # Dev lif kaçışı (von Reyn et al. 2014) ve MDN ile görsel geri çekilme (Sen et al. 2017)
    assert {Behavior.ESCAPE, Behavior.BACKWARD_WALKING} <= active(output)


@pytest.mark.veri
@requires_data
@pytest.mark.parametrize("category", ["geosmin", "co2"])
def test_koku_uyarimlari_yalnizca_devre(category: str) -> None:
    output = decode_scenario((category, 0.6))

    assert output.circuit_only is True
    assert active(output) == set()
    assert output.top_neuropils[0].neuropil.startswith(("AL_", "LH_"))


@pytest.mark.veri
@requires_data
def test_kalibrasyon_hazir_paketle_tutarli(tmp_path: Path) -> None:
    from sinek.decoder.calibration_build import build_calibration

    if not (PACKAGE / "co2@1.0.npz").is_file():
        pytest.skip("tekli senaryolar eksik")
    rebuilt = build_calibration(bundle(), PACKAGE, output=tmp_path / "kalibrasyon.json")
    stored = load_calibration()

    for behavior, entry in stored.items():
        fresh = rebuilt["behaviors"][behavior.value]  # type: ignore[index]
        assert (
            BehaviorCalibration(
                fresh["reference_rate_hz"], fresh["reference_scenario"], fresh["reference_group"]
            )
            == entry
        )
