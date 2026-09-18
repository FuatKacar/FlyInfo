import numpy as np
import pytest

from sinek.connectome.pipeline import IndexBundle
from sinek.lab.selection import (
    CellTypeSelector,
    GroupSelector,
    IdsSelector,
    NeuropilSelector,
    SelectionError,
    TransmitterSelector,
    indices_of,
    resolve_selector,
    search_cell_types,
)


def test_hazir_grup_secimi(bundle: IndexBundle) -> None:
    secim = resolve_selector(GroupSelector(group="uyarici"), bundle)

    assert secim.flywire_ids == (1000,)
    assert secim.label_tr == "uyarici grubu"
    assert indices_of(secim, bundle).tolist() == [0]


def test_hucre_tipi_secimi(bundle: IndexBundle) -> None:
    secim = resolve_selector(CellTypeSelector(cell_type="B"), bundle)

    assert secim.flywire_ids == (1001, 1002)  # mini ağda iki B tipi nöron


def test_norotransmitter_secimi(bundle: IndexBundle) -> None:
    secim = resolve_selector(TransmitterSelector(neurotransmitter="GABA"), bundle)

    assert secim.flywire_ids == (1001,)
    assert secim.label_tr == "gaba nöronları"


def test_noropil_secimi_cikis_sinapslarina_gore(bundle: IndexBundle) -> None:
    secim = resolve_selector(NeuropilSelector(neuropil="GNG"), bundle)

    assert secim.flywire_ids == (1000, 1001)  # çıkış sinapslarının çoğunluğu GNG'de


def test_kimlik_secimi_eksikleri_bildirir(bundle: IndexBundle) -> None:
    secim = resolve_selector(IdsSelector(ids=(1000, 424242)), bundle)

    assert secim.flywire_ids == (1000,)
    assert secim.missing_ids == (424242,)


@pytest.mark.parametrize(
    ("selector", "hata"),
    [
        (GroupSelector(group="yok"), "Bilinmeyen nöron grubu"),
        (CellTypeSelector(cell_type="ZZZ"), "hiçbir nörona"),
        (TransmitterSelector(neurotransmitter="kahve"), "Bilinmeyen nörotransmitter"),
        (NeuropilSelector(neuropil="XYZ"), "Bilinmeyen nöropil"),
        (IdsSelector(ids=(424242,)), "hiçbir nörona"),
    ],
)
def test_gecersiz_secimler_reddedilir(bundle: IndexBundle, selector: object, hata: str) -> None:
    with pytest.raises(SelectionError, match=hata):
        resolve_selector(selector, bundle)  # type: ignore[arg-type]


def test_hucre_tipi_aramasi_once_bastan_eslesenleri_verir(bundle: IndexBundle) -> None:
    sonuc = search_cell_types(bundle, "b")

    assert sonuc == [{"cell_type": "B", "neuron_count": 2}]
    with pytest.raises(SelectionError, match="boş olamaz"):
        search_cell_types(bundle, "   ")


def test_secim_kimlikleri_siralidir(bundle: IndexBundle) -> None:
    secim = resolve_selector(IdsSelector(ids=(1002, 1000)), bundle)

    assert secim.flywire_ids == (1000, 1002)
    assert np.array_equal(indices_of(secim, bundle), np.array([0, 2]))
