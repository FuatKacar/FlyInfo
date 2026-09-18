import json
from pathlib import Path

import pytest

from sinek.connectome.connectome import Connectome
from sinek.connectome.groups import Behavior
from sinek.connectome.pipeline import IndexBundle
from sinek.decoder.decoder import BehaviorCalibration
from sinek.lab.experiment import ExperimentRequest, LabParams, run_experiment
from sinek.lab.report import (
    REPORT_VERSION,
    ReportError,
    build_report,
    load_report,
    replay_report,
    save_report,
)
from tests.lab.conftest import CPU

PARAMS = LabParams(n_trials=5, t_run_ms=100.0, seed=11)
ISTEK = ExperimentRequest.model_validate(
    {
        "stimuli": [{"selector": {"kind": "group", "group": "uyarici"}, "rate_hz": 200.0}],
        "silenced": [{"kind": "ids", "ids": [1003]}],
        "params": PARAMS.model_dump(),
    }
)


@pytest.fixture
def rapor(
    bundle: IndexBundle, connectome: Connectome, calibration: dict[Behavior, BehaviorCalibration]
):  # type: ignore[no-untyped-def]
    sonuc = run_experiment(ISTEK, bundle, connectome, calibration, device=CPU)
    return build_report(ISTEK, sonuc, Path("data"), title_tr="Frenleyen nöron deneyi")


def test_rapor_kaynak_ve_surum_ozetlerini_tasir(rapor) -> None:  # type: ignore[no-untyped-def]
    assert rapor.report_version == REPORT_VERSION
    assert rapor.title_tr == "Frenleyen nöron deneyi"
    assert len(rapor.provenance.neuron_groups_definitions_sha256) == 64
    assert len(rapor.provenance.calibration_sha256) == 64
    assert rapor.provenance.environment["sinek"]
    assert rapor.request.params.seed == 11


def test_rapor_yazilip_geri_okunur(rapor, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    yol = save_report(tmp_path / "deney.json", rapor)

    geri = load_report(yol.read_text(encoding="utf-8"))

    assert geri == rapor
    assert json.loads(yol.read_text(encoding="utf-8"))["request"]["params"]["seed"] == 11


def test_bozuk_rapor_reddedilir() -> None:
    with pytest.raises(ReportError, match="okunamadı"):
        load_report("{ bu json değil")


def test_desteklenmeyen_surum_reddedilir(rapor) -> None:  # type: ignore[no-untyped-def]
    veri = json.loads(rapor.model_dump_json())
    veri["report_version"] = 999

    with pytest.raises(ReportError, match="sürümü desteklenmiyor"):
        load_report(veri)


def test_yeniden_kosma_ayni_sonucu_verir(
    rapor,  # type: ignore[no-untyped-def]
    bundle: IndexBundle,
    connectome: Connectome,
    calibration: dict[Behavior, BehaviorCalibration],
) -> None:
    tekrar = replay_report(rapor, bundle, connectome, calibration, Path("data"), device=CPU)

    assert tekrar.identical
    assert tekrar.differences == []
    assert tekrar.max_difference_hz == 0.0


def test_rapordaki_sonuc_degistirilmisse_fark_bildirilir(
    rapor,  # type: ignore[no-untyped-def]
    bundle: IndexBundle,
    connectome: Connectome,
    calibration: dict[Behavior, BehaviorCalibration],
) -> None:
    veri = json.loads(rapor.model_dump_json())
    veri["result"]["control"]["output"]["behaviors"][0]["rate_hz"] += 7.5
    bozuk = load_report(veri)

    tekrar = replay_report(bozuk, bundle, connectome, calibration, Path("data"), device=CPU)

    assert not tekrar.identical
    assert tekrar.max_difference_hz == pytest.approx(7.5)
    assert tekrar.differences[0].condition == "kontrol"
