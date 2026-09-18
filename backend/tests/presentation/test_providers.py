"""Sağlayıcıların geçici hata davranışı."""

import httpx
import pytest

from sinek.presentation.providers import (
    OpenAICompatibleProvider,
    ProviderError,
    with_retry,
)


@pytest.fixture(autouse=True)
def _hizli_bekleme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sinek.presentation.providers.time.sleep", lambda _s: None)


def test_gecici_hatada_yeniden_denenir() -> None:
    denemeler = []

    def call() -> str:
        denemeler.append(1)
        if len(denemeler) < 3:
            raise ProviderError("sunucu meşgul (503)", retryable=True)
        return "tamam"

    assert with_retry(call) == "tamam"
    assert len(denemeler) == 3


def test_kalici_hata_hemen_bildirilir() -> None:
    denemeler = []

    def call() -> str:
        denemeler.append(1)
        raise ProviderError("geçersiz anahtar (401)")

    with pytest.raises(ProviderError, match="401"):
        with_retry(call)
    assert len(denemeler) == 1


def test_tum_denemeler_tukenirse_hata_yukselir() -> None:
    def call() -> str:
        raise ProviderError("sunucu meşgul (503)", retryable=True)

    with pytest.raises(ProviderError, match="503"):
        with_retry(call, delays=(0.0,))


def _yanit(status: int) -> httpx.Response:
    request = httpx.Request("POST", "https://ornek.test/chat/completions")
    return httpx.Response(status, json={"error": "x"}, request=request)


@pytest.mark.parametrize(("status", "denenir"), [(503, 3), (429, 3), (401, 1)])
def test_durum_koduna_gore_yeniden_deneme(
    monkeypatch: pytest.MonkeyPatch, status: int, denenir: int
) -> None:
    cagrilar = []

    def sahte_post(*_args: object, **_kwargs: object) -> httpx.Response:
        cagrilar.append(1)
        return _yanit(status)

    monkeypatch.setattr("sinek.presentation.providers.httpx.post", sahte_post)
    provider = OpenAICompatibleProvider("https://ornek.test", "anahtar", "model-x")

    with pytest.raises(ProviderError, match=str(status)):
        provider.generate("sistem", "içerik")

    assert len(cagrilar) == denenir


def test_ag_kesintisi_gecici_sayilir(monkeypatch: pytest.MonkeyPatch) -> None:
    cagrilar = []

    def sahte_post(*_args: object, **_kwargs: object) -> httpx.Response:
        cagrilar.append(1)
        raise httpx.ConnectTimeout("zaman aşımı")

    monkeypatch.setattr("sinek.presentation.providers.httpx.post", sahte_post)
    provider = OpenAICompatibleProvider("https://ornek.test", "anahtar", "model-x")

    with pytest.raises(ProviderError, match="ConnectTimeout"):
        provider.generate("sistem", "içerik")

    assert len(cagrilar) == 3


def test_hata_metni_api_anahtarini_icermez(monkeypatch: pytest.MonkeyPatch) -> None:
    def sahte_post(*_args: object, **_kwargs: object) -> httpx.Response:
        return _yanit(401)

    monkeypatch.setattr("sinek.presentation.providers.httpx.post", sahte_post)
    provider = OpenAICompatibleProvider("https://ornek.test", "gizli-anahtar", "model-x")

    with pytest.raises(ProviderError) as hata:
        provider.generate("sistem", "içerik")

    assert "gizli-anahtar" not in str(hata.value)
