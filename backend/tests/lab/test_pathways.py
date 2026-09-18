import numpy as np
import pytest

from sinek.connectome.connectome import Connectome
from sinek.lab.pathways import PathwayError, strongest_paths

# Hızlar: 1000→40 Hz, 1001→30 Hz, 1002→20 Hz, 1003→10 Hz
HIZLAR = np.array([40.0, 30.0, 20.0, 10.0])


def test_en_guclu_yol_dogrudan_baglantidir(connectome: Connectome) -> None:
    yollar = strongest_paths(connectome, HIZLAR, np.array([0]), target=1)

    assert len(yollar) == 2
    ilk = yollar[0]
    assert ilk.hops == 1
    assert (ilk.edges[0].pre_id, ilk.edges[0].post_id) == ("1000", "1001")
    assert ilk.edges[0].synapses == 300
    assert ilk.edges[0].excitatory
    # 300 sinaps × 40 Hz / (300 × 40 + 150 × 10) = 0,889
    assert ilk.strength == pytest.approx(12000 / 13500)
    assert ilk.excitatory


def test_dolayli_yol_baskilayici_olarak_isaretlenir(connectome: Connectome) -> None:
    yollar = strongest_paths(connectome, HIZLAR, np.array([0]), target=1)

    dolayli = yollar[1]
    assert dolayli.hops == 2
    assert [e.post_id for e in dolayli.edges] == ["1003", "1001"]
    assert not dolayli.excitatory  # tek baskılayıcı kenar
    assert dolayli.strength == pytest.approx(1500 / 13500)
    assert dolayli.strength < yollar[0].strength


def test_yollar_gucune_gore_siralidir(connectome: Connectome) -> None:
    yollar = strongest_paths(connectome, HIZLAR, np.array([0]), target=2)

    guc = [y.strength for y in yollar]
    assert guc == sorted(guc, reverse=True)
    assert all(0 < g <= 1 for g in guc)


def test_sessiz_hedef_icin_yol_aranmaz(connectome: Connectome) -> None:
    sessiz = HIZLAR.copy()
    sessiz[1] = 0.0

    with pytest.raises(PathwayError, match="ateşlemedi"):
        strongest_paths(connectome, sessiz, np.array([0]), target=1)


def test_ateslemeyen_aracilar_yola_girmez(connectome: Connectome) -> None:
    """1003 sessizse yalnızca doğrudan yol kalır."""
    hizlar = HIZLAR.copy()
    hizlar[3] = 0.0

    yollar = strongest_paths(connectome, hizlar, np.array([0]), target=1)

    assert len(yollar) == 1
    assert yollar[0].strength == pytest.approx(1.0)


def test_adim_siniri_uygulanir(connectome: Connectome) -> None:
    yollar = strongest_paths(connectome, HIZLAR, np.array([0]), target=1, max_hops=1)

    assert [y.hops for y in yollar] == [1]


def test_kaynak_hedefe_ulasmiyorsa_bos_doner(connectome: Connectome) -> None:
    # 1002 (indeks 2) hiçbir nörona çıkmaz: ondan 1001'e yol yoktur.
    assert strongest_paths(connectome, HIZLAR, np.array([2]), target=1) == []
