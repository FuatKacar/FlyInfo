import json
import re
import struct

import numpy as np
import pytest

from sinek.schematic.build import (
    DEFAULT_OUTPUT,
    MeshError,
    front_view,
    parse_fragment,
    path_data,
    ring_area,
    silhouette,
    simplify,
)
from sinek.schematic.sources import NEUROPIL_MESHES


def fragment(vertices: list[list[float]], faces: list[list[int]]) -> bytes:
    return (
        struct.pack("<I", len(vertices))
        + np.asarray(vertices, "<f4").tobytes()
        + np.asarray(faces, "<u4").tobytes()
    )


def test_ag_parcasi_okunur() -> None:
    v, f = parse_fragment(fragment([[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 1, 2]]))

    assert v.shape == (3, 3)
    assert f.tolist() == [[0, 1, 2]]


@pytest.mark.parametrize(
    "data",
    [b"\x01", fragment([[0, 0, 0]], [[0, 1, 2]]), fragment([[0, 0, 0]], [])[:-2]],
    ids=["kisa", "gecersiz_dizin", "eksik_bayt"],
)
def test_bozuk_ag_parcasi_reddedilir(data: bytes) -> None:
    with pytest.raises(MeshError):
        parse_fragment(data)


def test_onden_gorunum_sagi_sola_cevirir_ve_um_yapar() -> None:
    points = front_view(np.array([[2000.0, 5000.0, 9000.0]]))

    assert points.tolist() == [[-2.0, 5.0]]


def test_kare_silueti_alani_korur() -> None:
    # 100 µm × 50 µm dikdörtgen, iki üçgen
    points = np.array([[10.0, 10.0], [110.0, 10.0], [110.0, 60.0], [10.0, 60.0]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])

    rings = silhouette(points, faces, origin=(0.0, 0.0), size=(120.0, 70.0))

    assert len(rings) == 1
    assert abs(ring_area(rings[0])) == pytest.approx(5000.0, rel=0.02)


def test_sadelestirme_dogrusal_noktalari_atar_koseleri_korur() -> None:
    line = np.array([[0.0, 0.0], [1.0, 0.01], [2.0, 0.0], [2.0, 5.0]])

    assert simplify(line, 0.1).tolist() == [[0.0, 0.0], [2.0, 0.0], [2.0, 5.0]]


def test_yol_verisi_kapali_halka_uretir() -> None:
    ring = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]])

    assert path_data([ring], np.zeros(2)) == "M0 0 10 0 10 10 0 10Z"


# --- Depodaki şema dosyası ------------------------------------------------------------------


@pytest.fixture(scope="module")
def schematic() -> dict[str, object]:
    data: dict[str, object] = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    return data


def centers(schematic: dict[str, object]) -> dict[str, tuple[float, float]]:
    return {n["name"]: tuple(n["center"]) for n in schematic["neuropils"]}  # type: ignore[attr-defined,index,misc]


def depths(schematic: dict[str, object]) -> dict[str, float]:
    return {n["name"]: n["depth_um"] for n in schematic["neuropils"]}  # type: ignore[attr-defined,index,misc]


def test_tum_nuropiller_ve_gecerli_yollar(schematic: dict[str, object]) -> None:
    neuropils = schematic["neuropils"]
    assert {n["name"] for n in neuropils} == set(NEUROPIL_MESHES)  # type: ignore[attr-defined,index]
    for n in neuropils:  # type: ignore[attr-defined]
        assert re.fullmatch(r"(M[-\d. ]+Z)+", n["d"]), n["name"]
    assert [n["depth_um"] for n in neuropils] == sorted(  # type: ignore[attr-defined]
        (n["depth_um"] for n in neuropils),
        reverse=True,  # type: ignore[attr-defined]
    )


def test_ad_eslemesi_sol_sag_ayna_simetrisiyle_tutarli(schematic: dict[str, object]) -> None:
    c = centers(schematic)
    midline = c["EB"][0]
    pairs = [n[:-2] for n in c if n.endswith("_L")]

    assert len(pairs) == 35  # 78 = 35 çift + 8 orta hat nöropili
    for base in pairs:
        right, left = c[f"{base}_R"], c[f"{base}_L"]
        assert right[0] < midline < left[0], base  # önden bakışta sineğin sağı solda
        assert abs((right[0] + left[0]) / 2 - midline) < 25, base
        assert abs(right[1] - left[1]) < 25, base


def test_ad_eslemesi_anatomik_konumlarla_tutarli(schematic: dict[str, object]) -> None:
    c, z = centers(schematic), depths(schematic)

    assert z["AL_R"] < z["MB_CA_R"]  # anten lobu önde, mantar cisim kaliksi arkada
    assert c["GNG"][1] > c["MB_CA_R"][1]  # GNG aşağıda
    assert c["LA_R"][0] < c["ME_R"][0] < c["LO_R"][0]  # optik lob dıştan içe
    for central in ("EB", "FB", "PB", "NO", "GNG", "PRW", "SAD"):
        assert abs(c[central][0] - c["EB"][0]) < 20, central


def test_sag_taraftaki_okuma_noronlari_solda_cizilir(schematic: dict[str, object]) -> None:
    midline = centers(schematic)["EB"][0]
    sided = [
        n
        for r in schematic["readouts"]  # type: ignore[attr-defined]
        for n in r["neurons"]
        if n["side"] in ("left", "right")
        and abs(n["point"][0] - midline) > 10  # orta hattakiler belirsiz
    ]

    assert sided
    for neuron in sided:
        assert (neuron["point"][0] < midline) == (neuron["side"] == "right"), neuron


# --- 3B geometri ------------------------------------------------------------------------------


def test_3b_eksenleri_onden_bakana_gore_cevrilir() -> None:
    from sinek.schematic.build3d import view_space

    nokta = view_space(np.array([[2000.0, 3000.0, 4000.0]]))

    # sağ → ekranın solu, ventral → aşağı, posterior → izleyiciden uzak
    assert nokta.tolist() == [[-2.0, -3.0, -4.0]]


def test_3b_dizinsiz_ag_kosleri_birlestirilir() -> None:
    from sinek.schematic.build3d import index_mesh

    # iki üçgen, ortak kenar: dizinsiz yığın olarak 6 köşe, gerçekte 4
    kose = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    ucgen = np.arange(6).reshape(2, 3)

    tekil, dizin = index_mesh(kose, ucgen)

    assert len(tekil) == 4
    assert dizin.shape == (2, 3)
    np.testing.assert_array_equal(tekil[dizin].reshape(-1, 3), kose)


def test_3b_dosyasi_dizinle_tutarli() -> None:
    import hashlib

    from sinek.schematic.build3d import DEFAULT_BINARY, DEFAULT_INDEX

    dizin = json.loads(DEFAULT_INDEX.read_text(encoding="utf-8"))
    veri = DEFAULT_BINARY.read_bytes()

    assert hashlib.sha256(veri).hexdigest() == dizin["binary_sha256"]
    assert dizin["index_byte_offset"] % 4 == 0
    son = dizin["parts"][-1]
    assert len(veri) == dizin["index_byte_offset"] + 4 * (son["index_offset"] + son["index_count"])
    assert {p["name"] for p in dizin["parts"]} - {"__beyin__"} == set(NEUROPIL_MESHES)
