"""Kural tabanlı uyarım sınıflandırıcısı (katman 1a).

Adımlar:
    1. Soru, gelecek zaman, koşul/dilek içeren mesaj → kapsam dışı
    2. Yan cümlelere böl; olumsuzluk içeren yan cümleler değerlendirilmez
    3. Her yan cümlede öncelikli ifadeleri, isimleri, fiil köklerini, anten ipuçlarını eşle
       (yazım hatası toleransı: uzun köklerde düzenleme mesafesi ≤ 1)
    4. Sıfatlar ("tatlı", "acı") yalnızca sunum ipucu veya aynı kategoriden isim varsa sayılır
    5. Kategori sözcüğü hemen ardından "gibi" geliyorsa mecaz sayılır (koku fiili yoksa)
    6. Yoğunluk: yan cümledeki zayıf/güçlü niceleyiciler (varsayılan orta)

Her karar bir kanıt kaydıyla döner; arayüz bunu "neden bu kategori" olarak gösterebilir.
"""

import re
from dataclasses import dataclass, field
from itertools import pairwise

from sinek.stimulus import lexicon as lx
from sinek.stimulus.text import Clause, clauses, edit_distance_at_most_one, fold, tokens


@dataclass(frozen=True)
class Evidence:
    category: str
    term: str
    clause: str
    rule: str


@dataclass(frozen=True)
class RuleResult:
    levels: dict[str, int]  # kategori → yoğunluk düzeyi (1–3)
    evidence: tuple[Evidence, ...]
    out_of_scope_reason: str | None = None
    notes: tuple[str, ...] = field(default=())


def _norm(term: str) -> str:
    """Sözlük terimi metinle aynı normalleştirmeden geçer (ör. 'salla' → 'sala')."""
    return fold(term)


_SOFTENING = {"k": "g", "p": "b", "t": "d", "c": "c"}
# Kısa fiil köklerinden sonra gelebilecek çekim ekleri (uç-uyor, kapat-tım)
_VERB_ENDING = re.compile(
    r"^(i|u)?(yor|du|di|tu|ti|dum|dim|tum|tim|ar|er|ir|ur|ip|up|arak|erek|mak|mek)"
)


def _stem_match(word: str, stem: str) -> bool:
    stem = _norm(stem)
    if word.startswith(stem) and lx.SUFFIX.match(word[len(stem) :]):
        return True
    # Ünsüz yumuşaması: toprak → toprağın, şurup → şurubu
    if stem[-1:] in _SOFTENING:
        soft = stem[:-1] + _SOFTENING[stem[-1]]
        if soft != stem and word.startswith(soft) and lx.SUFFIX.match(word[len(soft) :]):
            return True
    # Yazım hatası toleransı yalnızca uzun köklerde ve ilk harf aynıysa ("biraz" ≠ "kiraz")
    if len(stem) >= 5 and word[:1] == stem[:1]:
        for cut in (len(stem) - 1, len(stem), len(stem) + 1):
            if (
                0 < cut <= len(word)
                and edit_distance_at_most_one(word[:cut], stem)
                and lx.SUFFIX.match(word[cut:])
            ):
                return True
    return False


def _verb_match(word: str, stem: str) -> bool:
    if stem in lx.SHORT_VERB_FORMS:
        return word in {_norm(f) for f in lx.SHORT_VERB_FORMS[stem]}
    return word.startswith(_norm(stem))


def _message_level_exclusion(words: list[str], raw: str) -> str | None:
    if "?" in raw or any(lx.QUESTION_PARTICLES.match(w) for w in words):
        return "soru"
    if any(w in lx.TIME_WORDS for w in words):
        return "gelecek veya dilek"
    for w in words:
        if w in lx.FUTURE_EXCEPTIONS:
            continue
        if len(w) >= 6 and lx.FUTURE.search(w[2:]) and not lx.NEGATIVE_VERB.search(w):
            return "gelecek zaman"
        if lx.CONDITIONAL.search(w):
            return "koşul veya dilek"
    return None


def _is_negated(clause: Clause) -> bool:
    for w in clause.words:
        if w in lx.NEGATION_WORDS or w in {_norm(a) for a in lx.ABSENCE_WORDS}:
            return True
        if len(w) >= 5 and w not in lx.NOT_NEGATIVE and lx.NEGATIVE_VERB.search(w[2:]):
            return True
    return False


def has_presentation_cue(words: list[str] | tuple[str, ...]) -> bool:
    return any(w in lx.EXACT_CUES for w in words) or any(
        w.startswith(_norm(cue)) for w in words for cue in lx.PRESENTATION_CUES
    )


def _has_motion(words: tuple[str, ...]) -> bool:
    verbs = any(
        w == _norm(v)
        or (len(v) > 2 and w.startswith(_norm(v)))
        or (w.startswith(_norm(v)) and _VERB_ENDING.match(w[len(_norm(v)) :]))
        for w in words
        for v in lx.MOTION_VERBS
    )
    pairs = set(pairwise(words))
    direction = any(
        (len(d) == 1 and d[0] in words) or (len(d) == 2 and d in pairs) for d in lx.DIRECTION_WORDS
    )
    return verbs and direction


def intensity_level(clause: Clause) -> int:
    words = clause.words
    pairs = set(pairwise(words))
    if any(w in lx.STRONG_CUES for w in words) or pairs & set(lx.STRONG_PHRASES):
        return 3
    if any(w in lx.WEAK_CUES for w in words) or pairs & set(lx.WEAK_PHRASES):
        return 1
    return 2


def _simile(words: tuple[str, ...], position: int) -> bool:
    """Kategori sözcüğünden hemen sonra 'gibi' ve yan cümlede koku fiili yok → mecaz."""
    follows = position + 1 < len(words) and words[position + 1].startswith("gibi")
    return follows and not any(w.startswith("kok") for w in words)


def _clause_hits(clause: Clause, message_words: list[str]) -> list[Evidence]:
    words = clause.words
    used: set[int] = set()
    hits: list[Evidence] = []

    for phrase, categories in lx.PHRASES:
        n = len(phrase)
        for start in range(len(words) - n + 1):
            window = words[start : start + n]
            matched = all(
                w == _norm(part) if i < n - 1 else _stem_match(w, part)
                for i, (w, part) in enumerate(zip(window, phrase, strict=True))
            )
            if matched and not used & set(range(start, start + n)):
                used |= set(range(start, start + n))
                hits += [Evidence(c, " ".join(phrase), clause.raw, "ifade") for c in categories]

    nouns_found: set[str] = set()
    adjectives: list[tuple[str, str, int]] = []
    for position, word in enumerate(words):
        if position in used:
            continue
        for category, stems in lx.NOUNS.items():
            if any(_stem_match(word, s) for s in stems) and not _simile(words, position):
                hits.append(Evidence(category, word, clause.raw, "isim"))
                nouns_found.add(category)
                used.add(position)
        for category, stems in lx.VERB_STEMS.items():
            if position not in used and any(_verb_match(word, s) for s in stems):
                hits.append(Evidence(category, word, clause.raw, "fiil"))
                used.add(position)
        for category, stems in lx.ADJECTIVES.items():
            if (
                position not in used
                and any(_stem_match(word, s) for s in stems)
                and not _simile(words, position)
            ):
                adjectives.append((category, word, position))

    licensed = has_presentation_cue(message_words) or any(
        w.startswith(_norm(noun)) for w in message_words for noun in lx.SUBSTANCE_NOUNS
    )
    for category, word, _ in adjectives:
        if category in nouns_found or licensed:
            hits.append(Evidence(category, word, clause.raw, "sıfat+ipucu"))

    action = (
        has_presentation_cue(message_words)
        or _has_motion(words)
        or any(_verb_match(w, stem) for w in words for stem in lx.VERB_STEMS["looming"])
    )
    for position, word in enumerate(words):
        if position in used or not action:
            continue
        if any(_stem_match(word, obj) for obj in lx.LOOMING_OBJECTS):
            hits.append(Evidence("looming", word, clause.raw, "nesne+eylem"))
            used.add(position)
    if _has_motion(words) and not any(h.category == "looming" for h in hits):
        hits.append(Evidence("looming", "hareket+yön", clause.raw, "hareket"))

    if any(w.startswith(lx.ANTENNA_STEM) for w in words) and any(
        w.startswith(_norm(cue)) for w in words for cue in lx.ANTENNA_CUES
    ):
        hits.append(Evidence("johnston_organ", lx.ANTENNA_STEM, clause.raw, "anten+ipucu"))
    return hits


def _explicit_out_of_scope(words: list[str]) -> bool:
    for phrase in lx.OUT_OF_SCOPE_PHRASES:
        n = len(phrase)
        for start in range(len(words) - n + 1):
            window = words[start : start + n]
            if window[0].startswith(_norm(phrase[0])) and all(
                w.startswith(_norm(p)) for w, p in zip(window[1:], phrase[1:], strict=True)
            ):
                return True
    return False


def _topic_only(words: list[str]) -> bool:
    """Sunum ipucu yok ama bir konu fiili var → uyarıcı sözcüğü yalnızca konu."""
    if has_presentation_cue(words):
        return False
    return any(w.startswith(_norm(v)) for w in words for v in lx.TOPIC_VERBS)


def _post_filters(hits: list[Evidence], words: tuple[str, ...]) -> list[Evidence]:
    categories = {h.category for h in hits}
    result = []
    for hit in hits:
        if hit.category == "water" and hit.term.startswith("suyu"):
            index = words.index(hit.term) if hit.term in words else -1
            modifier = words[index - 1] if index > 0 else ""
            food = any(
                _stem_match(modifier, stem)
                for category in ("sugar", "bitter")
                for stem in lx.NOUNS[category]
            ) or any(modifier.startswith(_norm(m)) for m in lx.JUICE_MODIFIERS)
            adjective = modifier.endswith(("li", "lu"))  # "zehirli su" meyve suyu değildir
            if modifier and food and not adjective:
                continue  # "elma suyu", "tonik suyu": meyve suyu/içecek, su değil
        if (
            hit.category == "water"
            and hit.term.startswith(("islak", "yagmur"))
            and "geosmin" in categories
            and any(w.startswith(_norm(s)) for w in words for s in lx.SMELL_CONTEXT)
        ):
            continue  # "ıslak toprak kokusu"
        if hit.category == "sugar" and any(
            w.startswith(_norm(s)) for w in words for s in lx.SPOILAGE
        ):
            continue  # "küflü kek": bozulmuş yiyecek → kötü koku
        result.append(hit)
    return result


def classify_rules(text: str) -> RuleResult:
    words = tokens(text)
    reason = _message_level_exclusion(words, text)
    if reason:
        return RuleResult({}, (), out_of_scope_reason=reason)
    if _explicit_out_of_scope(words):
        return RuleResult({}, (), out_of_scope_reason="kapsam dışı ifade")

    levels: dict[str, int] = {}
    evidence: list[Evidence] = []
    negated = 0
    for clause in clauses(text):
        if _is_negated(clause):
            negated += 1
            continue
        hits = _post_filters(_clause_hits(clause, words), clause.words)
        level = intensity_level(clause)
        for hit in hits:
            evidence.append(hit)
            levels[hit.category] = max(levels.get(hit.category, 0), level)

    if "geosmin" not in levels and any(w.startswith("kok") for w in words):
        bad = [w for w in words if any(w.startswith(_norm(b)) for b in lx.BAD_SMELL_WORDS)]
        if bad and not _topic_only(words):
            evidence.append(Evidence("geosmin", bad[0], text, "kötü koku"))
            levels["geosmin"] = intensity_level(Clause(text, tuple(words)))
    if levels and _topic_only(words) and all(e.rule == "isim" for e in evidence):
        return RuleResult({}, tuple(evidence), out_of_scope_reason="yalnızca konu")
    if not levels:
        why = "olumsuzluk" if negated else "tanınan uyarıcı yok"
        return RuleResult({}, tuple(evidence), out_of_scope_reason=why)
    return RuleResult(levels, tuple(evidence))
