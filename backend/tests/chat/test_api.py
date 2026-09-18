from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sinek import __version__
from sinek.api.app import create_app
from sinek.chat.service import BrainService, ChatService, Services
from sinek.lab.service import LabService


def test_saglik_kontrolu() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": __version__,
        "llm_provider": "none",
        "llm_enabled": False,
    }


def test_derlenmis_arayuz_sunulur_api_onceliklidir(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html>arayuz</html>", encoding="utf-8")
    client = TestClient(create_app(web_dir=tmp_path))

    assert "arayuz" in client.get("/").text
    assert client.get("/api/health").json()["status"] == "ok"


def test_arayuz_derlenmemisse_yalnizca_api_sunulur(tmp_path: Path) -> None:
    client = TestClient(create_app(web_dir=tmp_path))

    assert client.get("/").status_code == 404


def test_veri_yoksa_anlasilir_hata_verir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINEK_DATA_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.post("/api/chat", json={"message": "bal"})

    assert response.status_code == 503
    assert "sinek indir" in response.json()["detail"]


@pytest.fixture
def client(brain: BrainService, chat: ChatService, tmp_path: Path) -> TestClient:
    lab = LabService(brain.index, tmp_path, tmp_path, {})
    return TestClient(create_app(lambda: Services(brain, chat, lab, None)))


def test_sohbet_tum_katmanlarin_ara_ciktisini_dondurur(client: TestClient) -> None:
    data = client.post("/api/chat", json={"message": "Sana biraz bal getirdim"}).json()

    assert data["classification"]["levels"] == {"sugar": 1}
    assert data["classification"]["evidence"][0]["category"] == "sugar"
    assert data["output"]["stimulus"]["scenario_key"] == "sugar@0.2"
    assert data["output"]["model"]["mode"] == "precomputed"
    assert data["presentation"]["source"] == "template"
    assert data["hint"] is None
    assert data["brain"]["neuropil_rates_hz"]["AL_L"] == 40.0
    assert data["brain"]["scale"] == {"reference_hz": 0.5, "max_hz": 200.0}


def test_kapsam_disi_mesajda_yonlendirme_gosterilir(client: TestClient) -> None:
    data = client.post("/api/chat", json={"message": "2+2 kaç eder?"}).json()

    assert data["classification"]["in_scope"] is False
    assert data["classification"]["out_of_scope_reason"]
    assert data["hint"]["examples"]
    assert data["output"]["stimulus"]["components"] == []


@pytest.mark.parametrize("message", ["", "a" * 1001], ids=["bos", "uzun"])
def test_gecersiz_mesaj_reddedilir(client: TestClient, message: str) -> None:
    assert client.post("/api/chat", json={"message": message}).status_code == 422


def test_dogrudan_uyarim(client: TestClient) -> None:
    response = client.post(
        "/api/stimulate", json={"components": [{"group": "water", "intensity": 0.6}]}
    )

    assert response.status_code == 200
    assert response.json()["output"]["model"]["mode"] == "live"
    assert set(response.json()["brain"]["neuropil_rates_hz"]) == {"AL_L", "GNG"}


@pytest.mark.parametrize(
    ("components", "detail"),
    [
        ([{"group": "yok", "intensity": 0.6}], "Bilinmeyen"),
        ([{"group": "mn9", "intensity": 0.6}], "Bilinmeyen"),
        ([{"group": "sugar", "intensity": 0.6}, {"group": "sugar", "intensity": 1.0}], "iki kez"),
        ([{"group": "sugar", "intensity": 0.25}], "0,1"),
    ],
)
def test_gecersiz_uyarim_reddedilir(
    client: TestClient, components: list[dict[str, object]], detail: str
) -> None:
    response = client.post("/api/stimulate", json={"components": components})

    assert response.status_code == 422
    assert detail in response.json()["detail"]


def test_senaryo_listesi_paket_durumunu_gosterir(client: TestClient) -> None:
    data = client.get("/api/scenarios").json()

    assert [g["key"] for g in data["groups"]] == ["sugar", "water", "geosmin"]
    assert data["groups"][2]["circuit_only"] is True
    assert data["package"] == {"available": True, "version": "1", "problem": None}
    precomputed = {s["key"] for s in data["scenarios"] if s["precomputed"]}
    assert precomputed == {"kontrol", "sugar@0.2"}


def test_hucre_tipi_sorgusu(client: TestClient) -> None:
    data = client.get("/api/neurons/T10").json()

    assert data["neuron_count"] == data["in_model_count"] == 1
    (neuron,) = data["neurons"]
    assert neuron["root_id"] == "10"
    assert neuron["groups"] == ["mn9"]

    missing_nt = client.get("/api/neurons/T20").json()["neurons"][0]
    assert missing_nt["top_nt"] is None
    assert missing_nt["top_nt_conf"] is None
    assert client.get("/api/neurons/YOK").status_code == 404
