import pytest

from sinek.decoder.schema import DecoderOutput, StimulusInfo
from sinek.presentation.locale import format_number, join_tr, lower_first_tr
from sinek.presentation.template import render_template
from sinek.presentation.validator import validate


def test_turkce_sayi_bicimi_ve_liste() -> None:
    assert format_number(38.24, 1) == "38,2"
    assert format_number(82.4, 0) == "82"
    assert join_tr(["a", "b", "c"]) == "a, b ve c"
    assert join_tr(["a"]) == "a"


def test_sablon_metni_json_ile_birebir(sugar_output: DecoderOutput) -> None:
    text = render_template(sugar_output)

    assert "Şekere duyarlı tat nöronları (160 Hz, 21 nöron) uyarıldı." in text
    assert "beslenme (hortum uzatma) %82 (MN9 38,2 Hz)" in text
    assert "GNG (%62) ve PRW (%7)" in text
    assert validate(text, sugar_output).valid  # şablon her zaman doğrulayıcıdan geçmeli


def test_turkce_ilk_harf_kucultme() -> None:
    assert lower_first_tr("Işık") == "ışık"
    assert lower_first_tr("İnen nöron") == "inen nöron"
    assert lower_first_tr("Şeker") == "şeker"


def test_uyarimsiz_sablon(sugar_output: DecoderOutput) -> None:
    output = sugar_output.model_copy(
        update={"stimulus": StimulusInfo(components=(), scenario_key="kontrol")}
    )

    assert render_template(output).startswith("Mesaj hiçbir duyusal kategoriyle eşleşmedi")


def test_sadik_llm_metni_kabul_edilir(sugar_output: DecoderOutput) -> None:
    text = (
        "Şekere duyarlı 21 tat nöronum 160 Hz ile uyarıldı. Beslenme devrem %82 düzeyinde etkin; "
        "MN9 motor nöronum 38,2 Hz ile ateşliyor. Kaçış ve anten temizleme devrelerim sessiz. "
        "En yoğun aktivite GNG bölgesinde (%62)."
    )

    result = validate(text, sugar_output)

    assert result.valid, result.problems


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("Beslenme devrem %95 etkin.", "karşılığı olmayan sayı: 95"),
        ("MN9 45 Hz ile ateşliyor, beslenme etkin.", "karşılığı olmayan sayı: 45"),
        ("Kaçış devrem de çalıştı, beslenme etkin.", "olumsuzlamasız anılmış: escape"),
        ("Tat nöronlarım uyarıldı.", "etkin davranış anılmamış: feeding"),
        ("Bala bayıldım, çok mutlu oldum; beslenme etkin.", "yasak ifade"),
        ("", "boş metin"),
    ],
)
def test_sadakatsiz_llm_metni_reddedilir(
    sugar_output: DecoderOutput, text: str, problem: str
) -> None:
    result = validate(text, sugar_output)

    assert not result.valid
    assert any(problem in p for p in result.problems), result.problems


def test_noron_adlarindaki_rakamlar_sayi_sayilmaz(sugar_output: DecoderOutput) -> None:
    assert validate("MN9 ve aDN1 kontrol edildi; beslenme %82 etkin.", sugar_output).valid
