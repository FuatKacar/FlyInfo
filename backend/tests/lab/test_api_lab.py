"""Laboratuvar uç noktaları (yapay devre; gerçek veri ve ekran kartı gerekmez)."""

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sinek.api.app import create_app
from sinek.chat.service import BrainService, ChatService, Services
from sinek.lab.service import LabService
from sinek.presentation.service import PresentationService
from sinek.simulation.store import ScenarioStore


def bitene_kadar(
    client: TestClient, yanit_json: dict[str, Any], sinir: float = 60.0
) -> dict[str, Any]:
    """İş bitene kadar durumunu yoklar (arka plan iş parçacığı)."""
    son = time.monotonic() + sinir
    durum = yanit_json
    while durum["state"] in ("queued", "running"):
        if time.monotonic() > sinir + son:
            raise AssertionError(f"iş bitmedi: {durum}")
        time.sleep(0.02)
        durum = client.get(f"/api/lab/jobs/{durum['id']}").json()
    return durum


ISTEK: dict[str, Any] = {
    "stimuli": [{"selector": {"kind": "group", "group": "uyarici"}, "rate_hz": 200.0}],
    "silenced": [{"kind": "ids", "ids": [1003]}],
    "params": {"n_trials": 4, "t_run_ms": 100.0, "seed": 5},
}


@pytest.fixture
def client(lab_service: LabService) -> TestClient:  # type: ignore[no-untyped-def]
    brain = BrainService(lab_service.index, ScenarioStore(None, None), {})
    chat = ChatService(brain, PresentationService([], None))
    return TestClient(create_app(lambda: Services(brain, chat, lab_service, None)))


def test_secenekler_gruplari_ve_sinirlari_verir(client: TestClient) -> None:
    veri = client.get("/api/lab/options").json()

    assert {g["key"] for g in veri["groups"]} >= {"uyarici", "feeding"}
    assert veri["neuropils"] == ["GNG", "PRW"]
    assert "gaba" in veri["neurotransmitters"]
    assert veri["limits"]["max_rate_hz"] == 400
    assert veri["busy"] is False


def test_hucre_tipi_aramasi(client: TestClient) -> None:
    veri = client.get("/api/neurons/search", params={"q": "b"}).json()

    assert veri == [{"cell_type": "B", "neuron_count": 2}]
    assert client.get("/api/neurons/search", params={"q": ""}).status_code == 422


def test_deney_kontrol_ve_susturmayi_dondurur(client: TestClient) -> None:
    yanit = client.post("/api/lab/run", json=ISTEK)

    assert yanit.status_code == 202
    assert yanit.json()["state"] in ("queued", "running")
    durum = bitene_kadar(client, yanit.json())
    assert durum["state"] == "done"
    assert durum["progress"] == 1
    veri = durum["experiment"]
    assert veri["silenced_neuron_count"] == 1
    assert veri["silenced_condition"]["label_tr"] == "susturma"
    beslenme = next(c for c in veri["comparisons"] if c["behavior"] == "feeding")
    assert beslenme["silenced_rate_hz"] > beslenme["control_rate_hz"]  # fren kalktı
    assert 0 <= beslenme["p_value"] <= 1


@pytest.mark.parametrize(
    ("govde", "beklenen"),
    [
        ({"stimuli": []}, 422),
        ({"stimuli": [{"selector": {"kind": "group", "group": "yok"}, "rate_hz": 100}]}, 422),
        ({"stimuli": [{"selector": {"kind": "group", "group": "uyarici"}, "rate_hz": 900}]}, 422),
    ],
)
def test_gecersiz_deney_reddedilir(client: TestClient, govde: dict, beklenen: int) -> None:
    yanit = client.post("/api/lab/run", json=govde)
    if yanit.status_code == 202:  # seçim hatası işin içinde ortaya çıkar
        durum = bitene_kadar(client, yanit.json())
        assert durum["state"] == "error"
        assert durum["error_tr"]
    else:
        assert yanit.status_code == beklenen


def test_sinyal_yollari_hedef_ve_sinirlilik_notuyla_doner(client: TestClient) -> None:
    yanit = client.post(
        "/api/lab/pathways", json={"experiment": ISTEK, "behavior": "feeding", "top_k": 3}
    )

    assert yanit.status_code == 202
    veri = bitene_kadar(client, yanit.json())["pathways"]
    assert veri["target_id"] == "1001"
    assert veri["pathways"][0]["edges"][0]["pre_id"] == "1000"
    assert veri["pathways"][0]["edges"][0]["pre_cell_type"] == "A"  # anotasyondan okunur ad
    assert veri["pathways"][0]["edges"][0]["post_cell_type"] == "B"
    assert veri["pathways"][0]["strength"] > 0
    assert "nedensellik kanıtı değildir" in veri["note_tr"]


def test_sessiz_davranis_icin_yol_hatasi(client: TestClient) -> None:
    """Kaçış okuması (1002) yalnızca baskılayıcı girdi alır: hiç ateşlemez."""
    yanit = client.post("/api/lab/pathways", json={"experiment": ISTEK, "behavior": "escape"})

    durum = bitene_kadar(client, yanit.json())

    assert durum["state"] == "error"
    assert "ateşlemedi" in durum["error_tr"]


def test_rapor_uretilir_ve_geri_yuklenince_ayni_sonucu_verir(client: TestClient) -> None:
    rapor = bitene_kadar(
        client,
        client.post(
            "/api/lab/report", json={"experiment": ISTEK, "title_tr": "Fren deneyi"}
        ).json(),
    )["report"]

    assert rapor["title_tr"] == "Fren deneyi"
    assert len(rapor["provenance"]["neuron_groups_definitions_sha256"]) == 64

    tekrar = bitene_kadar(client, client.post("/api/lab/replay", json=rapor).json())["replay"]

    assert tekrar["identical"] is True
    assert tekrar["max_difference_hz"] == 0
    assert tekrar["differences"] == []


def test_bozuk_rapor_reddedilir(client: TestClient) -> None:
    yanit = client.post("/api/lab/replay", json={"report_version": 999})  # işe girmeden reddedilir

    assert yanit.status_code == 422
    assert "Rapor" in yanit.json()["detail"]


def test_mesgulken_yeni_deney_reddedilir(client: TestClient, lab_service: LabService) -> None:
    lab_service._lock.acquire()
    try:
        yanit = client.post("/api/lab/run", json=ISTEK)
    finally:
        lab_service._lock.release()

    assert yanit.status_code == 409
    assert "çalışıyor" in yanit.json()["detail"]


def test_rapor_dosyasi_json_olarak_saklanabilir(client: TestClient, tmp_path) -> None:  # type: ignore[no-untyped-def]
    rapor = bitene_kadar(client, client.post("/api/lab/report", json={"experiment": ISTEK}).json())[
        "report"
    ]
    yol = tmp_path / "deney.json"
    yol.write_text(json.dumps(rapor, ensure_ascii=False), encoding="utf-8")

    geri = json.loads(yol.read_text(encoding="utf-8"))

    assert geri["request"]["params"]["seed"] == 5
    assert geri["result"]["stimuli"][0]["flywire_ids"] == ["1000"]  # kimlikler metin


def test_bilinmeyen_is_bulunamadi_doner(client: TestClient) -> None:
    assert client.get("/api/lab/jobs/yok").status_code == 404


def test_is_ilerlemesi_bildirilir(client: TestClient) -> None:
    durum = bitene_kadar(client, client.post("/api/lab/run", json=ISTEK).json())

    assert durum["step_tr"] == "tamamlandı"
    assert durum["experiment"]["control"]["label_tr"] == "kontrol"


def test_buyuk_kimlikler_metin_olarak_tasinir(client: TestClient) -> None:
    """FlyWire kimlikleri 2^53'ten büyüktür; JSON'da metin taşınmazsa tarayıcıda bozulur."""
    yanit = client.post(
        "/api/lab/run",
        json={
            **ISTEK,
            "silenced": [{"kind": "ids", "ids": ["1003"]}],
        },
    )

    durum = bitene_kadar(client, yanit.json())

    assert durum["state"] == "done"
    assert durum["experiment"]["silenced"][0]["flywire_ids"] == ["1003"]


def test_ornek_deneyler_listelenir_ve_yuklenir(client: TestClient) -> None:
    liste = client.get("/api/lab/examples").json()

    adlar = {o["name"] for o in liste}
    assert {"seker-yolu-susturma", "aci-beslenmeyi-baskilar"} <= adlar
    rapor = client.get("/api/lab/examples/seker-yolu-susturma").json()
    assert "şekil 1F" in rapor["title_tr"]
    assert rapor["request"]["silenced"][0]["ids"] == ["720575940623211725"]
    beslenme = next(c for c in rapor["result"]["comparisons"] if c["behavior"] == "feeding")
    assert beslenme["control_rate_hz"] > beslenme["silenced_rate_hz"]


@pytest.mark.parametrize("ad", ["yok", "../../etc/passwd", "BUYUK"])
def test_bilinmeyen_ornek_bulunamadi(client: TestClient, ad: str) -> None:
    assert client.get(f"/api/lab/examples/{ad}").status_code == 404
