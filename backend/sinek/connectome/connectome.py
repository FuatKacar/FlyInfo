"""İşaretli seyrek bağlantı matrisi.

Matris yönelimi `weights[post, pre]` şeklindedir: bir nörona gelen toplam girdi
`weights @ presinaptik_aktivite` ile hesaplanır. Değerler işaretli sinaps sayısıdır.
"""

from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from numpy.typing import NDArray

# Referans modelin işaret kuralı (Connectivity_783.parquet ile doğrulanmıştır, bkz. docs/veri.md)
EXCITATORY_TRANSMITTERS = frozenset({"acetylcholine", "dopamine", "serotonin", "octopamine"})
INHIBITORY_TRANSMITTERS = frozenset({"gaba", "glutamate"})


class SignSource(StrEnum):
    """Sinaps işaretinin (uyarıcı / baskılayıcı) nereden alınacağı."""

    REFERENCE = "reference"  # Shiu et al. 2024 bağlantı tablosu (makaleyle birebir karşılaştırma)
    ANNOTATIONS = "annotations"  # güncel FlyWire anotasyonlarındaki top_nt tahmini


class ConnectomeError(ValueError):
    """Ham veri beklenen yapıda veya tutarlılıkta değil."""


def _index_of(
    flywire_ids: NDArray[np.int64], order: NDArray[np.int64], ids: list[int] | NDArray[np.int64]
) -> tuple[NDArray[np.int64], list[int]]:
    sorted_ids = flywire_ids[order]
    query = np.asarray(ids, dtype=np.int64)
    positions = np.clip(np.searchsorted(sorted_ids, query), 0, max(flywire_ids.size - 1, 0))
    found = sorted_ids[positions] == query
    missing = [int(i) for i in query[~found]]
    return order[positions[found]], missing


@dataclass(frozen=True, eq=False)
class NeuronIndex:
    """Yalnızca nöron kimlik listesi: bağlantı matrisi gerektirmeyen işler için (ör. hazır senaryo
    çözümleme). Kimlik sırası `Connectome` ile aynıdır, aynı dosyadan okunur."""

    flywire_ids: NDArray[np.int64]

    @property
    def n_neurons(self) -> int:
        return int(self.flywire_ids.size)

    def index_of(self, ids: list[int] | NDArray[np.int64]) -> tuple[NDArray[np.int64], list[int]]:
        """FlyWire kimliklerini model indekslerine çevirir; bulunamayanları ayrıca döndürür."""
        return _index_of(self.flywire_ids, self._sorted_order, ids)

    @cached_property
    def _sorted_order(self) -> NDArray[np.int64]:
        return np.argsort(self.flywire_ids, kind="stable").astype(np.int64)


@dataclass(frozen=True, eq=False)
class Connectome:
    flywire_ids: NDArray[np.int64]
    weights: sp.csr_array
    sign_source: SignSource
    sign_overrides: int = 0  # anotasyon işaretinin referanstan farklı olduğu nöron sayısı

    @property
    def n_neurons(self) -> int:
        return int(self.flywire_ids.size)

    @property
    def n_connections(self) -> int:
        return int(self.weights.nnz)

    @property
    def n_synapses(self) -> int:
        # float32 toplamı büyük değerlerde yuvarlama hatası yapar; float64'te topla.
        return int(np.abs(self.weights.data).sum(dtype=np.float64))

    def index_of(self, ids: list[int] | NDArray[np.int64]) -> tuple[NDArray[np.int64], list[int]]:
        """FlyWire kimliklerini model indekslerine çevirir; bulunamayanları ayrıca döndürür."""
        return _index_of(self.flywire_ids, self._sorted_order, ids)

    @cached_property
    def _sorted_order(self) -> NDArray[np.int64]:
        return np.argsort(self.flywire_ids, kind="stable").astype(np.int64)


def load_neuron_index(completeness_path: Path) -> NeuronIndex:
    return NeuronIndex(_load_neuron_ids(completeness_path))


def _load_neuron_ids(completeness_path: Path) -> NDArray[np.int64]:
    completeness = pd.read_csv(completeness_path, index_col=0)
    ids = completeness.index.to_numpy(dtype=np.int64)
    if np.unique(ids).size != ids.size:
        raise ConnectomeError("Nöron listesinde yinelenen kimlik var.")
    return ids


def _annotation_signs(
    flywire_ids: NDArray[np.int64], annotations: pd.DataFrame
) -> NDArray[np.int8]:
    """Anotasyondaki top_nt'den nöron başına işaret; bilinmiyorsa 0."""
    transmitter = annotations["top_nt"].reindex(flywire_ids).str.lower()
    signs = np.zeros(flywire_ids.size, dtype=np.int8)
    signs[transmitter.isin(EXCITATORY_TRANSMITTERS).to_numpy()] = 1
    signs[transmitter.isin(INHIBITORY_TRANSMITTERS).to_numpy()] = -1
    return signs


def build_connectome(
    completeness_path: Path,
    connectivity_path: Path,
    sign_source: SignSource = SignSource.REFERENCE,
    annotations: pd.DataFrame | None = None,
) -> Connectome:
    """Ham tablolardan bağlantı matrisini kurar ve tutarlılığını doğrular."""
    flywire_ids = _load_neuron_ids(completeness_path)
    n = flywire_ids.size

    table = pd.read_parquet(
        connectivity_path,
        columns=[
            "Presynaptic_ID",
            "Postsynaptic_ID",
            "Presynaptic_Index",
            "Postsynaptic_Index",
            "Connectivity",
            "Excitatory",
        ],
    )
    pre = table["Presynaptic_Index"].to_numpy(dtype=np.int64)
    post = table["Postsynaptic_Index"].to_numpy(dtype=np.int64)
    count = table["Connectivity"].to_numpy(dtype=np.int64)
    reference_sign = table["Excitatory"].to_numpy(dtype=np.int64)

    if pre.size and (min(pre.min(), post.min()) < 0 or max(pre.max(), post.max()) >= n):
        raise ConnectomeError("Bağlantı tablosunda nöron listesi dışında indeks var.")
    if not (
        np.array_equal(flywire_ids[pre], table["Presynaptic_ID"].to_numpy(dtype=np.int64))
        and np.array_equal(flywire_ids[post], table["Postsynaptic_ID"].to_numpy(dtype=np.int64))
    ):
        raise ConnectomeError(
            "Bağlantı tablosundaki kimlik ↔ indeks eşlemesi nöron listesiyle uyuşmuyor."
        )
    if (count <= 0).any():
        raise ConnectomeError("Sinaps sayısı pozitif olmayan bağlantı var.")
    if not np.isin(reference_sign, (-1, 1)).all():
        raise ConnectomeError("Referans işaret sütunu yalnızca -1 / +1 içermeli.")

    sign = reference_sign
    overrides = 0
    if sign_source is SignSource.ANNOTATIONS:
        if annotations is None:
            raise ValueError("Anotasyon işaret kaynağı için anotasyon tablosu gerekir.")
        neuron_sign = _annotation_signs(flywire_ids, annotations)
        edge_sign = neuron_sign[pre].astype(np.int64)
        # Anotasyonda nörotransmitteri bilinmeyen nöronlar referans işaretini korur.
        sign = np.where(edge_sign != 0, edge_sign, reference_sign)
        reference_neuron_sign = np.zeros(n, dtype=np.int64)
        reference_neuron_sign[pre] = reference_sign
        overrides = int(
            (
                (neuron_sign != 0)
                & (reference_neuron_sign != 0)
                & (neuron_sign != reference_neuron_sign)
            ).sum()
        )

    values = (count * sign).astype(np.float32)
    weights = sp.coo_array((values, (post, pre)), shape=(n, n)).tocsr()
    weights.sum_duplicates()
    if weights.nnz != len(table):
        raise ConnectomeError("Bağlantı tablosunda yinelenen (pre, post) çifti var.")

    return Connectome(
        flywire_ids=flywire_ids,
        weights=weights,
        sign_source=sign_source,
        sign_overrides=overrides,
    )


def load_annotations(path: Path) -> pd.DataFrame:
    """Kullanılan anotasyon sütunlarını `root_id` indeksiyle yükler."""
    columns = [
        "root_id",
        "super_class",
        "cell_class",
        "cell_sub_class",
        "cell_type",
        "hemibrain_type",
        "side",
        "top_nt",
        "top_nt_conf",
    ]
    frame = pd.read_csv(
        path, sep="\t", usecols=columns, dtype={"root_id": np.int64}, low_memory=False
    )
    if frame["root_id"].duplicated().any():
        raise ConnectomeError("Anotasyon tablosunda yinelenen root_id var.")
    return frame.set_index("root_id")
