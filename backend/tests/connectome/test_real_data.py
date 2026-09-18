"""Gerçek FlyWire v783 verisiyle entegrasyon testleri.

Veri yoksa atlanır. Çalıştırmak için: `uv run sinek indir` ardından `uv run pytest -m veri`.
"""

from functools import cache
from pathlib import Path

import numpy as np
import pytest

from sinek.connectome.connectome import SignSource
from sinek.connectome.pipeline import DataBundle, format_report, load_bundle, raw_dir
from sinek.connectome.sources import SOURCES

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

pytestmark = [
    pytest.mark.veri,
    pytest.mark.skipif(
        not all((raw_dir(DATA_DIR) / s.filename).is_file() for s in SOURCES),
        reason="FlyWire verisi indirilmemiş (uv run sinek indir)",
    ),
]


@cache
def bundle(sign_source: SignSource = SignSource.REFERENCE) -> DataBundle:
    return load_bundle(DATA_DIR, sign_source)


def test_konektom_boyutlari_yayinlanan_degerlerle_tutarli() -> None:
    c = bundle().connectome

    assert c.n_neurons == 138_639  # Shiu et al. v783 tamamlanmış nöron listesi
    assert c.n_connections == 15_091_983
    assert c.n_synapses == 54_492_922  # Dorkenwald et al. 2024: ~5×10⁷ kimyasal sinaps


def test_isaret_dagilimi() -> None:
    signs = np.sign(bundle().connectome.weights.data)

    assert (signs > 0).sum() == 9_059_302
    assert (signs < 0).sum() == 6_032_681


def test_referans_gruplarinin_v783_eslesmesi() -> None:
    groups = bundle().groups

    # (nöron, kayıp, ardılla değiştirilen) — v630 → v783 kimlik değişimleri CAVE ile çözüldü;
    # gruplar makaledeki boyutlarla aynıdır. docs/veri.md bölüm 4.3
    expected = {
        "sugar": (21, 0, 1),
        "bitter": (21, 0, 1),
        "water": (18, 0, 0),
        "ir94e": (18, 0, 0),
        "johnston_organ": (146, 0, 1),
    }
    for key, sizes in expected.items():
        g = groups[key]
        assert (g.size, len(g.missing_ids), len(g.substituted)) == sizes, key
        assert len(set(g.flywire_ids)) == g.size, f"{key}: yinelenen nöron"


def test_ardil_noronlar_dogru_hucre_tipinde() -> None:
    b = bundle()
    annotations = b.annotations

    for key, expected_sub_class in (("sugar", "sugar/water"), ("bitter", "bitter")):
        ((_, new),) = b.groups[key].substituted
        assert annotations.loc[new, "cell_sub_class"] == expected_sub_class
    ((_, jo_new),) = b.groups["johnston_organ"].substituted
    assert str(annotations.loc[jo_new, "cell_type"]).startswith("JO-")


def test_anotasyon_gruplari_ve_okuma_noronlari() -> None:
    groups = bundle().groups

    expected = {
        "looming": 314,
        "geosmin": 39,
        "co2": 67,
        "mn9": 2,
        "giant_fiber": 2,
        "adn1": 2,
        "adn2": 2,
        "mdn": 4,
        "p9": 2,
        "abn1": 2,
    }
    assert {k: groups[k].size for k in expected} == expected
    assert 720575940660219265 in groups["mn9"].flywire_ids  # referans kodundaki MN9


def test_tat_gruplari_dogru_alt_sinifta() -> None:
    b = bundle()
    sub_class = b.annotations["cell_sub_class"]

    assert set(sub_class.loc[list(b.groups["sugar"].flywire_ids)]) == {"sugar/water"}
    assert set(sub_class.loc[list(b.groups["bitter"].flywire_ids)]) == {"bitter"}
    assert set(sub_class.loc[list(b.groups["water"].flywire_ids)]) == {"sugar/water"}


def test_anotasyon_isaret_farki_belgelenen_duzeyde() -> None:
    c = bundle(SignSource.ANNOTATIONS).connectome

    assert c.sign_overrides == 6_021
    assert c.n_synapses == 54_492_922


def test_ozet_rapor_turkce_bicimli_ve_eksiksiz() -> None:
    report = format_report(bundle())

    assert "54.492.922" in report  # Türkçe binlik ayırıcı
    assert "BOŞ!" not in report
    assert report.count("[TAMAM]") == len(bundle().groups)
