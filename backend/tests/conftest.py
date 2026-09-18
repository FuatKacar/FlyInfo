import os
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest

from sinek.config import get_settings


@pytest.fixture(autouse=True)
def _clean_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[None]:
    """Testlerin geliştiricinin .env dosyasından ve SINEK_ ortam değişkenlerinden etkilenmemesi."""
    for key in list(os.environ):
        if key.startswith("SINEK_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path_factory.mktemp("calisma"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# Yapay mini konektom: 4 nöron, bilinen bağlantılar ve anotasyonlar.
#
# indeks  kimlik  top_nt          cell_type
# 0       1000    acetylcholine   A
# 1       1001    gaba            B
# 2       1002    glutamate       B
# 3       1003    acetylcholine   C   (referans işareti -1: anotasyonla çelişir)
IDS = [1000, 1001, 1002, 1003]
# (pre, post, sinaps sayısı, referans işareti)
EDGES = [(0, 1, 5, 1), (1, 2, 3, -1), (2, 0, 2, -1), (3, 0, 7, -1), (0, 3, 1, 1)]


@pytest.fixture
def mini_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    completeness = tmp_path / "completeness.csv"
    pd.DataFrame({"Completed": [True] * len(IDS)}, index=pd.Index(IDS, name="")).to_csv(
        completeness
    )

    connectivity = tmp_path / "connectivity.parquet"
    pd.DataFrame(
        {
            "Presynaptic_ID": [IDS[p] for p, *_ in EDGES],
            "Postsynaptic_ID": [IDS[q] for _, q, *_ in EDGES],
            "Presynaptic_Index": [p for p, *_ in EDGES],
            "Postsynaptic_Index": [q for _, q, *_ in EDGES],
            "Connectivity": [n for *_, n, _ in EDGES],
            "Excitatory": [s for *_, s in EDGES],
            "Excitatory x Connectivity": [n * s for *_, n, s in EDGES],
        }
    ).to_parquet(connectivity)

    annotations = tmp_path / "annotations.tsv"
    pd.DataFrame(
        {
            "root_id": [*IDS, 9999],  # 9999: modelde olmayan nöron
            "super_class": ["central"] * 5,
            "cell_class": [None] * 5,
            "cell_sub_class": [None] * 5,
            "cell_type": ["A", "B", "B", "C", "B"],
            "hemibrain_type": [None] * 5,
            "side": ["left", "left", "right", "right", "left"],
            "top_nt": ["acetylcholine", "gaba", "glutamate", "acetylcholine", "gaba"],
            "top_nt_conf": [0.9] * 5,
        }
    ).to_csv(annotations, sep="\t", index=False)

    return completeness, connectivity, annotations
