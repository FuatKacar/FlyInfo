from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sinek.connectome.connectome import (
    ConnectomeError,
    SignSource,
    build_connectome,
    load_annotations,
)

Files = tuple[Path, Path, Path]


def test_matris_yonelimi_post_pre_ve_isaretli(mini_files: Files) -> None:
    completeness, connectivity, _ = mini_files

    c = build_connectome(completeness, connectivity)
    w = c.weights.toarray()

    assert c.n_neurons == 4
    assert c.n_connections == 5
    assert c.n_synapses == 5 + 3 + 2 + 7 + 1
    assert w[1, 0] == 5  # 0 → 1 uyarıcı
    assert w[2, 1] == -3  # 1 → 2 baskılayıcı
    assert w[0, 3] == -7  # 3 → 0 referans işareti
    assert w[0, 1] == 0  # ters yönde bağlantı yok


def test_anotasyon_isaret_kaynagi_referansi_gecersiz_kilar(mini_files: Files) -> None:
    completeness, connectivity, annotations_path = mini_files
    annotations = load_annotations(annotations_path)

    c = build_connectome(completeness, connectivity, SignSource.ANNOTATIONS, annotations)
    w = c.weights.toarray()

    assert w[0, 3] == 7  # nöron 3 asetilkolin → uyarıcı
    assert c.sign_overrides == 1
    assert c.sign_source is SignSource.ANNOTATIONS


def test_anotasyon_isareti_anotasyonsuz_istenemez(mini_files: Files) -> None:
    completeness, connectivity, _ = mini_files

    with pytest.raises(ValueError, match="anotasyon"):
        build_connectome(completeness, connectivity, SignSource.ANNOTATIONS)


def test_kimlikten_indekse_eslem_ve_kayiplar(mini_files: Files) -> None:
    completeness, connectivity, _ = mini_files
    c = build_connectome(completeness, connectivity)

    indices, missing = c.index_of([1003, 42, 1000])

    assert indices.tolist() == [3, 0]
    assert missing == [42]


def test_tutarsiz_kimlik_indeks_eslemesi_reddedilir(mini_files: Files) -> None:
    completeness, connectivity, _ = mini_files
    table = pd.read_parquet(connectivity)
    table.loc[0, "Presynaptic_ID"] = 1002
    table.to_parquet(connectivity)

    with pytest.raises(ConnectomeError, match="eşlemesi"):
        build_connectome(completeness, connectivity)


def test_yinelenen_baglanti_reddedilir(mini_files: Files) -> None:
    completeness, connectivity, _ = mini_files
    table = pd.read_parquet(connectivity)
    pd.concat([table, table.iloc[[0]]]).to_parquet(connectivity)

    with pytest.raises(ConnectomeError, match="yinelenen"):
        build_connectome(completeness, connectivity)


def test_buyuk_sinaps_toplami_yuvarlanmaz(mini_files: Files) -> None:
    completeness, connectivity, _ = mini_files
    c = build_connectome(completeness, connectivity)
    c.weights.data[:] = np.float32(16_777_217)  # float32'de tam gösterilemeyen toplamlar

    assert c.n_synapses == 5 * 16_777_216
