"""Türkçe metin ön işleme: küçük harf, karakter katlama, sözcük ve yan cümle bölme.

Karakter katlama (ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u) hem metne hem sözlüğe uygulanır; böylece
Türkçe karakter kullanmadan yazılmış mesajlar ("sekerli su") aynı biçimde eşleşir.
"""

import re
import unicodedata
from dataclasses import dataclass

_FOLD = str.maketrans(
    {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"}
)
_WORD = re.compile(r"[a-z0-9]+")
# Yan cümle sınırları: noktalama ve bağlaçlar
_CLAUSE_PUNCTUATION = re.compile(r"[,;.!?]+")
CONJUNCTIONS = frozenset(
    {"ama", "fakat", "ancak", "ve", "ile", "hem", "yoksa", "veya", "ya", "diye"}
)


def lower_tr(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı")
    return unicodedata.normalize("NFC", text).lower()


def fold(text: str) -> str:
    """Türkçe küçük harf + karakter katlama + ardışık aynı harflerin teke indirilmesi."""
    folded = lower_tr(text).translate(_FOLD)
    return re.sub(r"([a-z])\1+", r"\1", folded)


def tokens(text: str) -> list[str]:
    return _WORD.findall(fold(text))


@dataclass(frozen=True)
class Clause:
    raw: str
    words: tuple[str, ...]


def clauses(text: str) -> list[Clause]:
    """Metni noktalama ve bağlaçlarda yan cümlelere böler."""
    result: list[Clause] = []
    for chunk in _CLAUSE_PUNCTUATION.split(text):
        current: list[str] = []
        raw_words = chunk.split()
        raw_current: list[str] = []
        for raw_word in raw_words:
            words = tokens(raw_word)
            if len(words) == 1 and words[0] in CONJUNCTIONS:
                if current:
                    result.append(Clause(" ".join(raw_current), tuple(current)))
                current, raw_current = [], []
                continue
            current.extend(words)
            raw_current.append(raw_word)
        if current:
            result.append(Clause(" ".join(raw_current), tuple(current)))
    return result


def edit_distance_at_most_one(a: str, b: str) -> bool:
    """Damerau-Levenshtein mesafesi ≤ 1 mi (ekleme, silme, değiştirme, komşu yer değiştirme)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return (
            len(diff) == 2
            and diff[1] == diff[0] + 1
            and a[diff[0]] == b[diff[1]]
            and a[diff[1]] == b[diff[0]]
        )
    short, long_ = (a, b) if la < lb else (b, a)
    return any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))
