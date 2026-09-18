"""Uygulama ayarları.

Tüm ayarlar `SINEK_` önekli ortam değişkenlerinden veya `.env` dosyasından okunur.
Hiçbir API anahtarı zorunlu değildir.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    """Sunum katmanında kullanılabilecek LLM sağlayıcıları."""

    NONE = "none"
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SINEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: LLMProvider = LLMProvider.NONE

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.5-flash-lite"

    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3"

    host: str = "127.0.0.1"
    port: int = 8000

    data_dir: Path = Path("data")
    artifacts_dir: Path = Path("artifacts")
    cache_dir: Path = Path("cache")

    @property
    def llm_enabled(self) -> bool:
        """Seçili sağlayıcı gerçekten kullanılabilir durumda mı (anahtarı var mı)?"""
        match self.llm_provider:
            case LLMProvider.GEMINI:
                return self.gemini_api_key is not None
            case LLMProvider.GROQ:
                return self.groq_api_key is not None
            case LLMProvider.OLLAMA:
                return True
            case LLMProvider.NONE:
                return False


@lru_cache
def get_settings() -> Settings:
    return Settings()
