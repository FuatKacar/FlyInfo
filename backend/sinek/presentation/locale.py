"""Kullanıcıya görünen Türkçe metinler (`locales/tr.json`) ve Türkçe sayı biçimi."""

import json
from functools import cache
from pathlib import Path
from typing import Any

LOCALE_PATH = Path(__file__).resolve().parent.parent / "locales" / "tr.json"


@cache
def texts() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(LOCALE_PATH.read_text(encoding="utf-8"))
    return data


def format_number(value: float, decimals: int = 1) -> str:
    """Türkçe ondalık ayırıcı: 38.25 → '38,3' (decimals=1), 82.4 → '82' (decimals=0)."""
    text = f"{value:.{decimals}f}"
    return text.replace(".", ",")


def join_tr(items: list[str]) -> str:
    """['a', 'b', 'c'] → 'a, b ve c'."""
    if len(items) <= 1:
        return "".join(items)
    conjunction = str(texts()["template"]["list_and"])
    return ", ".join(items[:-1]) + conjunction + items[-1]


def lower_first_tr(text: str) -> str:
    """Türkçe kurala göre ilk harfi küçültür: 'İ' → 'i', 'I' → 'ı'."""
    if not text:
        return text
    first = {"İ": "i", "I": "ı"}.get(text[0], text[0].lower())
    return first + text[1:]
