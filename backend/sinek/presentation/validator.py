"""LLM çıktısının `DecoderOutput`'a sadakat denetimi.

Kurallar (herhangi biri ihlal edilirse metin reddedilir ve şablon metin kullanılır):
    1. Metindeki her sayı, JSON'daki bir değerin gösterim biçimlerinden biriyle eşleşmeli.
    2. Etkin davranışların her biri metinde anılmalı.
    3. Etkin olmayan bir davranış yalnızca olumsuzlama içeren bir cümlede anılabilir.
    4. Duygu, niyet veya bilinç atfeden sözcükler kullanılamaz.
    5. Metin boş olamaz ve üst uzunluk sınırını aşamaz.
"""

import re
import unicodedata
from dataclasses import dataclass

from sinek.decoder.schema import DecoderOutput
from sinek.presentation.locale import texts

MAX_CHARACTERS = 700
# Önünde harf/rakam olan rakamlar sayı sayılmaz: MN9, aDN1, P9, v783 gibi adlar denetime girmez.
_NUMBER = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+")


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    problems: tuple[str, ...]


def _lower_tr(text: str) -> str:
    # Türkçe büyük/küçük harf: İ → i, I → ı
    text = text.replace("İ", "i").replace("I", "ı")
    return unicodedata.normalize("NFC", text.lower())


def allowed_values(output: DecoderOutput) -> list[float]:
    """Metinde geçebilecek sayısal değerler (yüzdeler 0–100 ölçeğinde)."""
    values: list[float] = [output.active_neuron_count, output.model.n_trials]
    for c in output.stimulus.components:
        values += [c.rate_hz, c.neuron_count]
        if c.intensity is not None:
            values += [c.intensity, 100 * c.intensity]
    for b in output.behaviors:
        values += [b.rate_hz, b.rate_std_hz]
        if b.score is not None:
            values += [b.score, 100 * b.score]
    for n in output.top_neuropils:
        values += [n.events_hz, n.share, 100 * n.share]
    return [float(v) for v in values]


def _matches(written: str, values: list[float]) -> bool:
    """Yazılan sayı, bir JSON değerinin aynı ondalık basamakta yuvarlanmışı veya kesilmişi mi?

    Tolerans yazılan basamak sayısından hesaplanır: "32,3" için ±0,05 (yuvarlama) ya da değerin
    0,1'den küçük bir fazlası (kesme; 32,35 → "32,3"). Uydurulmuş sayılar yine yakalanır.
    """
    text = written.replace(",", ".")
    try:
        number = float(text)
    except ValueError:  # pragma: no cover - _NUMBER yalnızca sayı yakalar
        return False
    decimals = len(text.partition(".")[2])
    # Kayan nokta payı: 32,35 gibi değerler ikili gösterimde tam tutulmaz.
    unit = 10.0**-decimals
    epsilon = 1e-6  # kayan nokta payı: 32,35 gibi değerler ikili gösterimde tam tutulmaz
    return any(
        abs(number - value) <= 0.5 * unit + epsilon or -epsilon <= value - number < unit
        for value in values
    )


def allowed_numbers(output: DecoderOutput) -> set[str]:
    """Kabul edilen gösterimler (testler ve hata ayıklama için; 0 ve 1 ondalık)."""
    forms: set[str] = set()
    for value in allowed_values(output):
        for decimals in (0, 1):
            rounded = f"{value:.{decimals}f}"
            forms.add(rounded)
            forms.add(rounded.replace(".", ","))
    return forms


def validate(text: str, output: DecoderOutput) -> ValidationResult:
    problems: list[str] = []
    stripped = text.strip()
    if not stripped:
        return ValidationResult(False, ("boş metin",))
    if len(stripped) > MAX_CHARACTERS:
        problems.append(f"metin {MAX_CHARACTERS} karakteri aşıyor")

    values = allowed_values(output)
    for number in _NUMBER.findall(stripped):
        if not _matches(number, values):
            problems.append(f"JSON'da karşılığı olmayan sayı: {number}")

    lowered = _lower_tr(stripped)
    sentences = [_lower_tr(s) for s in _SENTENCE_SPLIT.split(stripped)]
    negations = [_lower_tr(n) for n in texts()["presentation"]["negations"]]
    keywords: dict[str, list[str]] = texts()["behavior_keywords"]

    for behavior in output.behaviors:
        words = [_lower_tr(w) for w in keywords[behavior.behavior.value]]
        mentioned = [s for s in sentences if any(w in s for w in words)]
        if behavior.active and not mentioned:
            problems.append(f"etkin davranış anılmamış: {behavior.behavior.value}")
        if not behavior.active:
            for sentence in mentioned:
                if not any(n in sentence for n in negations):
                    problems.append(
                        f"etkin olmayan davranış olumsuzlamasız anılmış: {behavior.behavior.value}"
                    )
                    break

    for word in texts()["presentation"]["forbidden_words"]:
        if re.search(rf"\b{re.escape(_lower_tr(word))}", lowered):
            problems.append(f"yasak ifade (duygu/niyet atfı): {word}")

    return ValidationResult(not problems, tuple(problems))
