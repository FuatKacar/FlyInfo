"""Sunum servisi: DecoderOutput → Türkçe yanıt.

Akış:
    1. Önbellekte bu çıktı için doğrulanmış bir LLM yanıtı varsa onu döndür.
    2. Sağlayıcıları sırayla dene; her yanıtı doğrulayıcıdan geçir.
    3. Hiçbiri geçerli yanıt üretemezse şablon metni döndür (neden kaydedilir).

LLM'e yalnızca çözümleyici JSON'u gönderilir; kullanıcının mesajı gönderilmez.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sinek.decoder.schema import DecoderOutput
from sinek.presentation.locale import texts
from sinek.presentation.providers import Provider, ProviderError
from sinek.presentation.template import render_template
from sinek.presentation.validator import validate

PROMPT_VERSION = "2"
# Sunum katmanının toplam süre bütçesi: aşılırsa şablon metne düşülür ve kullanıcı beklemez.
BUDGET_SECONDS = 45.0

SYSTEM_PROMPT = """Sen bir meyve sineği (Drosophila) beyin simülasyonunun SUNUM KATMANISIN.
Görevin, sana verilen JSON'daki simülasyon sonucunu 2-4 kısa Türkçe cümleyle, sineğin ağzından
(birinci tekil) okunabilir hale getirmektir.

KESİN KURALLAR:
- Yalnızca JSON'daki bilgiyi kullan. JSON'da olmayan hiçbir sayı, nöron, bölge veya davranış ekleme.
- Uyarıcıların adını JSON'daki "name_tr" alanından al; İngilizce terim (ör. looming, sugar) yazma.
- Sayıları JSON'daki değerlerden yuvarlayarak yaz (en fazla 1 ondalık, Türkçe virgül: 38,2).
  Skorları yüzde olarak yaz (0.82 → %82).
- "active": true olan HER davranışı an. "active": false olan davranışları ya hiç anma ya da
  açıkça olumsuz söyle (ör. "kaçış devrem sessiz").
- Duygu, niyet, düşünce, istek veya bilinç atfetme (ör. mutlu, korktu, istiyor, seviyor YASAK).
  Yalnızca nöral aktiviteyi anlat.
- "circuit_only": true ise, davranış iddia etmeden yalnızca devre aktivitesini anlat.
- Uyarım bileşeni yoksa, mesajın hiçbir duyusal kategoriyle eşleşmediğini söyle.
- Sadece yanıt metnini yaz; başlık, liste, JSON veya açıklama ekleme."""


@dataclass(frozen=True)
class Presentation:
    text: str
    source: Literal["llm", "template"]
    provider: str | None = None
    model: str | None = None
    fallback_reason: str | None = None


def _payload(output: DecoderOutput) -> str:
    data = output.model_dump(mode="json", exclude={"model": {"seed"}})
    labels = texts()["behaviors"]
    for behavior in data["behaviors"]:
        behavior["label_tr"] = labels[behavior["behavior"]]
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def cache_key(output: DecoderOutput, provider: Provider) -> str:
    raw = f"{PROMPT_VERSION}|{provider.name}|{provider.model}|{_payload(output)}"
    return hashlib.sha256(raw.encode()).hexdigest()


class PresentationService:
    def __init__(
        self,
        providers: list[Provider],
        cache_dir: Path | None,
        budget_seconds: float = BUDGET_SECONDS,
    ) -> None:
        self._providers = providers
        self._cache_dir = cache_dir
        self._budget = budget_seconds

    def present(self, output: DecoderOutput) -> Presentation:
        if not self._providers:
            return Presentation(render_template(output), "template", fallback_reason="LLM kapalı")

        reasons = []
        payload = _payload(output)
        deadline = time.monotonic() + self._budget
        for provider in self._providers:
            cached = self._read_cache(output, provider)
            if cached is not None:
                return Presentation(cached, "llm", provider.name, provider.model)
            if time.monotonic() >= deadline:
                reasons.append(f"{provider.name}/{provider.model}: süre bütçesi doldu")
                break
            try:
                text = provider.generate(SYSTEM_PROMPT, payload).strip()
            except ProviderError as error:
                reasons.append(f"{provider.name}/{provider.model}: {error}")
                continue
            result = validate(text, output)
            if result.valid:
                self._write_cache(output, provider, text)
                return Presentation(text, "llm", provider.name, provider.model)
            reasons.append(f"{provider.name}/{provider.model}: {'; '.join(result.problems)}")

        return Presentation(
            render_template(output), "template", fallback_reason=" | ".join(reasons)
        )

    def _cache_path(self, output: DecoderOutput, provider: Provider) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / "llm" / f"{cache_key(output, provider)}.txt"

    def _read_cache(self, output: DecoderOutput, provider: Provider) -> str | None:
        path = self._cache_path(output, provider)
        if path is None or not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        # Önbellek de doğrulanır: doğrulayıcı kuralları sıkılaşmışsa eski yanıt kullanılmaz.
        return text if validate(text, output).valid else None

    def _write_cache(self, output: DecoderOutput, provider: Provider, text: str) -> None:
        path = self._cache_path(output, provider)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
