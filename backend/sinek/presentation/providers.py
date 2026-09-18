"""LLM sağlayıcıları. Hepsi aynı arayüzü uygular: sistem istemi + kullanıcı içeriği → metin.

Hata durumunda `ProviderError` fırlatılır; üst katman (service.py) şablon metne düşer.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx

from sinek.config import LLMProvider, Settings

TIMEOUT_SECONDS = 25.0
TEMPERATURE = 0.2  # sadakat öncelikli: düşük yaratıcılık
# Geçici hatalarda (sunucu meşgul, hız sınırı) bekleme süreleri; ücretsiz katmanda sık görülür.
RETRY_DELAYS_SECONDS = (1.0, 3.0)
# Yalnızca HIZLI başarısızlıklar yeniden denenir: zaman aşımına uğramış bir çağrıyı tekrarlamak
# kullanıcıyı dakikalarca bekletir; sunucu meşgul yanıtları ise saniyenin altında döner.
RETRY_MAX_ATTEMPT_SECONDS = 5.0
RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class ProviderError(RuntimeError):
    """Sağlayıcı yanıt veremedi (ağ, kota, yapılandırma)."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


def with_retry[T](call: Callable[[], T], delays: tuple[float, ...] = RETRY_DELAYS_SECONDS) -> T:
    """Geçici ve hızlı başarısızlıklarda yeniden dener; kalıcı ya da yavaş hatada vazgeçer."""
    for delay in delays:
        started = time.monotonic()
        try:
            return call()
        except ProviderError as error:
            slow = time.monotonic() - started > RETRY_MAX_ATTEMPT_SECONDS
            if not error.retryable or slow:
                raise
            time.sleep(delay)
    return call()


def _status_code(error: Exception) -> int | None:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def _status_text(error: Exception) -> str:
    status = _status_code(error)
    return f" ({status})" if status is not None else ""


def _is_retryable(error: Exception) -> bool:
    status = _status_code(error)
    if status is not None:
        return status in RETRYABLE_STATUS
    return isinstance(error, httpx.TransportError)  # ağ kesintisi, zaman aşımı


class Provider(Protocol):
    name: str
    model: str

    def generate(self, system: str, content: str) -> str: ...


@dataclass
class GeminiProvider:
    api_key: str
    model: str
    name: str = "gemini"

    def generate(self, system: str, content: str) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:  # pragma: no cover - bağımlılık kurulumuna bağlı
            raise ProviderError("google-genai paketi kurulu değil") from error

        # SDK'nın "otomatik işlev çağrısı" uyarısı bu kullanımda anlamsız; konsolu kirletmesin.
        logging.getLogger("google_genai.models").setLevel(logging.ERROR)

        def call() -> str:
            try:
                client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=int(TIMEOUT_SECONDS * 1000)),
                )
                response = client.models.generate_content(
                    model=self.model,
                    contents=content,
                    config=types.GenerateContentConfig(
                        system_instruction=system, temperature=TEMPERATURE
                    ),
                )
            except Exception as error:  # SDK çok çeşitli hata türleri fırlatır
                # Anahtarın hata metnine sızmaması için yalnızca tür ve durum kodu aktarılır.
                status = getattr(error, "code", None)
                retryable = isinstance(status, int) and status in RETRYABLE_STATUS
                detail = f" ({status})" if isinstance(status, int) else ""
                raise ProviderError(
                    f"Gemini hatası: {type(error).__name__}{detail}", retryable=retryable
                ) from error
            text = response.text
            if not text:
                raise ProviderError("Gemini boş yanıt döndürdü")
            return text

        return with_retry(call)


@dataclass
class OpenAICompatibleProvider:
    """Groq (OpenAI uyumlu /chat/completions uç noktası)."""

    base_url: str
    api_key: str
    model: str
    name: str = "groq"

    def generate(self, system: str, content: str) -> str:
        return with_retry(lambda: self._call(system, content))

    def _call(self, system: str, content: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": TEMPERATURE,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": content},
                    ],
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
            raise ProviderError(
                f"{self.name} hatası: {type(error).__name__}{_status_text(error)}",
                retryable=_is_retryable(error),
            ) from error
        if not isinstance(text, str) or not text.strip():
            raise ProviderError(f"{self.name} boş yanıt döndürdü")
        return text


@dataclass
class OllamaProvider:
    base_url: str
    model: str
    name: str = "ollama"

    def generate(self, system: str, content: str) -> str:
        return with_retry(lambda: self._call(system, content))

    def _call(self, system: str, content: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {"temperature": TEMPERATURE},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": content},
                    ],
                },
                timeout=TIMEOUT_SECONDS * 4,  # yerel model ilk yüklemede yavaş olabilir
            )
            response.raise_for_status()
            text = response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise ProviderError(
                f"Ollama hatası: {type(error).__name__}{_status_text(error)}",
                retryable=_is_retryable(error),
            ) from error
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("Ollama boş yanıt döndürdü")
        return text


def providers_from_settings(settings: Settings) -> list[Provider]:
    """Yapılandırmaya göre denenecek sağlayıcılar (öncelik sırasıyla)."""
    if not settings.llm_enabled:
        return []
    match settings.llm_provider:
        case LLMProvider.GEMINI:
            assert settings.gemini_api_key is not None
            key = settings.gemini_api_key.get_secret_value()
            return [
                GeminiProvider(key, settings.gemini_model),
                GeminiProvider(key, settings.gemini_fallback_model),
            ]
        case LLMProvider.GROQ:
            assert settings.groq_api_key is not None
            return [
                OpenAICompatibleProvider(
                    "https://api.groq.com/openai/v1",
                    settings.groq_api_key.get_secret_value(),
                    settings.groq_model,
                )
            ]
        case LLMProvider.OLLAMA:
            return [OllamaProvider(settings.ollama_url, settings.ollama_model)]
        case LLMProvider.NONE:
            return []
