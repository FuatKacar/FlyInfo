"""Sınıflandırıcı davranış ve regresyon testleri."""

import pytest

from sinek.stimulus.classifier import classify
from sinek.stimulus.evaluate import evaluate, load_examples
from sinek.stimulus.text import clauses, edit_distance_at_most_one, fold


def test_turkce_katlama_ve_harf_sadelestirme() -> None:
    assert fold("Şekerli ÇİKOLATA") == "sekerli cikolata"
    assert fold("suuu") == "su"
    assert fold("Işık") == "isik"


def test_yan_cumle_bolme() -> None:
    parts = [c.words for c in clauses("Bal koydum ama içine zehir kattım, sonra gittim")]

    assert parts == [("bal", "koydum"), ("icine", "zehir", "katim"), ("sonra", "gitim")]


def test_duzenleme_mesafesi() -> None:
    assert edit_distance_at_most_one("zehir", "zeher")
    assert edit_distance_at_most_one("karbondioksit", "karbondiyoksit")
    assert edit_distance_at_most_one("abc", "acb")
    assert not edit_distance_at_most_one("bal", "balik")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sana biraz bal getirdim", {"sugar": 1}),
        ("Önüne bir kova su boşalttım", {"water": 3}),
        ("sekerli su koydum", {"sugar": 2, "water": 2}),
        ("Elimi sana doğru yaklaştırıyorum", {"looming": 2}),
        ("Antenlerine hafifçe üfledim", {"johnston_organ": 1}),
        ("Nemli toprağın kokusu yayılıyor", {"geosmin": 2}),
    ],
)
def test_uyarici_ve_yogunluk(text: str, expected: dict[str, int]) -> None:
    result = classify(text)

    assert result.levels == expected
    assert result.in_scope
    assert result.evidence  # her karar kanıtla açıklanır


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("Sana bal vermeyeceğim", None),
        ("Bal mı seversin su mu?", "soru"),
        ("Yarın sana şeker getireceğim", None),
        ("Acı biberi önüne koydum", "kapsam dışı ifade"),
        ("Arılar bal yapar", "yalnızca konu"),
        ("Merhaba, nasılsın", "tanınan uyarıcı yok"),
    ],
)
def test_kapsam_disi(text: str, reason: str | None) -> None:
    result = classify(text)

    assert result.levels == {}
    assert result.out_of_scope_reason is not None
    if reason:
        assert result.out_of_scope_reason == reason


@pytest.mark.parametrize(("name", "minimum"), [("gelistirme", 0.95), ("gelistirme2", 0.95)])
def test_gelistirme_setlerinde_gerileme_yok(name: str, minimum: float) -> None:
    assert evaluate(lambda t: classify(t).levels, load_examples(name)).macro_f1 >= minimum


def test_muhurlu_test_setinde_kabul_olcutu() -> None:
    """Faz 4 kabul ölçütü (makro F1 ≥ 0,85). Kurallar bu test setine göre ayarlanmaz."""
    assert evaluate(lambda t: classify(t).levels, load_examples("test")).macro_f1 >= 0.85
