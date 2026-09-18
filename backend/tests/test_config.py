import pytest

from sinek.config import LLMProvider, Settings


def test_varsayilan_ayarlar_anahtarsiz_calisir() -> None:
    settings = Settings()

    assert settings.llm_provider is LLMProvider.NONE
    assert settings.llm_enabled is False


def test_gemini_anahtar_yoksa_devre_disi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINEK_LLM_PROVIDER", "gemini")

    assert Settings().llm_enabled is False


def test_gemini_anahtar_varsa_etkin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINEK_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("SINEK_GEMINI_API_KEY", "test-anahtari")

    settings = Settings()

    assert settings.llm_enabled is True
    assert settings.gemini_model == "gemini-3.8-flash"


def test_api_anahtari_disari_sizmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINEK_GEMINI_API_KEY", "gizli-deger")

    assert "gizli-deger" not in repr(Settings())
