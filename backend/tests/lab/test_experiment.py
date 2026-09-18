import numpy as np
import pytest

from sinek.connectome.connectome import Connectome
from sinek.connectome.groups import Behavior
from sinek.connectome.pipeline import IndexBundle
from sinek.decoder.decoder import BehaviorCalibration
from sinek.lab.experiment import (
    ExperimentRequest,
    LabParams,
    LabStimulus,
    run_experiment,
)
from sinek.lab.selection import SelectionError
from tests.lab.conftest import CPU

PARAMS = LabParams(n_trials=6, t_run_ms=100.0, seed=3)


def istek(**extra: object) -> ExperimentRequest:
    return ExperimentRequest.model_validate(
        {
            "stimuli": [{"selector": {"kind": "group", "group": "uyarici"}, "rate_hz": 200.0}],
            "params": PARAMS.model_dump(),
            **extra,
        }
    )


def calistir(
    request: ExperimentRequest,
    bundle: IndexBundle,
    connectome: Connectome,
    calibration: dict[Behavior, BehaviorCalibration],
):  # type: ignore[no-untyped-def]
    return run_experiment(request, bundle, connectome, calibration, device=CPU)


def test_uyarim_calisir_ve_cozumleyiciden_gecer(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    sonuc = calistir(istek(), bundle, connectome, calibration)

    assert sonuc.silenced_condition is None
    assert sonuc.comparisons == []
    bilesen = sonuc.control.output.stimulus.components[0]
    assert (bilesen.rate_hz, bilesen.neuron_count) == (200.0, 1)
    assert bilesen.name_tr == "uyarici grubu"
    assert sonuc.control.output.model.n_trials == 6
    assert set(sonuc.control.neuropil_rates_hz) == {"GNG", "PRW"}
    assert sonuc.duration_seconds >= 0


def test_susturma_kontrolle_karsilastirilir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    # 1000 → 1001 tek uyarıcı girdidir: 1000 susturulunca beslenme okuması (1001) tamamen susar.
    sonuc = calistir(
        istek(silenced=[{"kind": "ids", "ids": [1000]}]), bundle, connectome, calibration
    )

    assert sonuc.silenced_neuron_count == 1
    assert sonuc.silenced_condition is not None
    beslenme = next(c for c in sonuc.comparisons if c.behavior is Behavior.FEEDING)
    assert beslenme.control_rate_hz > 0
    assert beslenme.silenced_rate_hz == 0
    assert beslenme.difference_hz < 0
    assert beslenme.percent_change == pytest.approx(-100)
    assert beslenme.significant


def test_ayni_tohum_ayni_sonucu_verir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    a = calistir(istek(), bundle, connectome, calibration)
    b = calistir(istek(), bundle, connectome, calibration)

    assert a.control.output.behaviors == b.control.output.behaviors


def test_farkli_tohum_farkli_denemeler_uretir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    a = calistir(istek(), bundle, connectome, calibration)
    b = calistir(
        istek(params=PARAMS.model_copy(update={"seed": 99}).model_dump()),
        bundle,
        connectome,
        calibration,
    )

    assert a.control.output.active_neuron_count >= 1
    assert a.control.output.behaviors != b.control.output.behaviors


def test_genis_susturma_uyari_verir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    sonuc = calistir(
        istek(silenced=[{"kind": "ids", "ids": [1001, 1002]}]), bundle, connectome, calibration
    )

    assert any("fizyolojik olmayan" in u for u in sonuc.warnings_tr)


def test_okuma_noronu_susturulursa_aciklayici_uyari_verilir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    """Susturma çıkış sinapslarını kapatır; okuma nöronunun kendi hızı ölçülmeye devam eder."""
    sonuc = calistir(
        istek(silenced=[{"kind": "ids", "ids": [1001]}]), bundle, connectome, calibration
    )

    assert any("okuma nöronudur" in u for u in sonuc.warnings_tr)
    beslenme = next(c for c in sonuc.comparisons if c.behavior is Behavior.FEEDING)
    assert beslenme.silenced_rate_hz > 0  # kendi ateşlemesi sürer


def test_eksik_kimlik_uyari_olarak_bildirilir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    sonuc = calistir(
        istek(
            stimuli=[
                {"selector": {"kind": "ids", "ids": [1000, 424242]}, "rate_hz": 150.0},
            ]
        ),
        bundle,
        connectome,
        calibration,
    )

    assert any("424242" in u or "1 kimlik" in u for u in sonuc.warnings_tr)


def test_gecersiz_grup_reddedilir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    with pytest.raises(SelectionError):
        calistir(
            istek(stimuli=[{"selector": {"kind": "group", "group": "yok"}, "rate_hz": 100.0}]),
            bundle,
            connectome,
            calibration,
        )


@pytest.mark.parametrize(
    ("alan", "deger"),
    [("rate_hz", 0), ("rate_hz", 401), ("rate_hz", -5)],
)
def test_gecersiz_frekans_reddedilir(alan: str, deger: float) -> None:
    with pytest.raises(ValueError, match="rate_hz"):
        LabStimulus.model_validate({"selector": {"kind": "group", "group": "a"}, alan: deger})


@pytest.mark.parametrize(
    ("alan", "deger"),
    [("n_trials", 0), ("n_trials", 51), ("t_run_ms", 99), ("t_run_ms", 5000)],
)
def test_gecersiz_parametreler_reddedilir(alan: str, deger: float) -> None:
    with pytest.raises(ValueError, match=alan):
        LabParams.model_validate({alan: deger})


def test_uyarim_yoksa_istek_gecersiz() -> None:
    with pytest.raises(ValueError, match="stimuli"):
        ExperimentRequest.model_validate({"stimuli": []})


def test_yuksek_frekansta_yogunluk_bos_birakilir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    """Yoğunluk (0-1) yalnızca sohbet ızgarasında anlamlıdır; 200 Hz üstünde tanımsızdır."""
    sonuc = calistir(
        istek(stimuli=[{"selector": {"kind": "group", "group": "uyarici"}, "rate_hz": 300.0}]),
        bundle,
        connectome,
        calibration,
    )

    assert sonuc.control.output.stimulus.components[0].intensity is None


def test_deneme_basina_hizlar_istatistige_girer(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    sonuc = calistir(
        istek(silenced=[{"kind": "ids", "ids": [1003]}]), bundle, connectome, calibration
    )

    for karsilastirma in sonuc.comparisons:
        assert 0 <= karsilastirma.p_value <= 1
        assert np.isfinite(karsilastirma.difference_hz)


def test_frenleyen_noron_susturulunca_davranis_guclenir(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
) -> None:
    """3 (1003) beslenme okumasını baskılar; susturulunca beslenme hızı artmalıdır."""
    sonuc = calistir(
        istek(silenced=[{"kind": "ids", "ids": [1003]}]), bundle, connectome, calibration
    )

    beslenme = next(c for c in sonuc.comparisons if c.behavior is Behavior.FEEDING)
    assert beslenme.silenced_rate_hz > beslenme.control_rate_hz
    assert beslenme.percent_change is not None
    assert beslenme.percent_change > 0
