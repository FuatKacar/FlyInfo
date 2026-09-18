"""Nöropil (beyin bölgesi) aktivite özeti.

Bir nöropilin aktivitesi, o bölgede saniyede gerçekleşen tahmini sinaptik çıkış olayı sayısıdır:

    aktivite(bölge) = Σ_nöron  ateşleme_hızı(nöron) × çıkış_sinapsı_sayısı(nöron, bölge)

Kaynak: FlyWire v783 `per_neuron_neuropil_count_pre_783` (Dorkenwald et al. 2024).
Bölge boyutundan bağımsız karşılaştırma için sinaps ağırlıklı ortalama hız da hesaplanır:

    ortalama_hız(bölge) = aktivite(bölge) / Σ_nöron çıkış_sinapsı_sayısı(nöron, bölge)    [Hz]

Hiçbir nöropile atanmamış sinapslar ("None") özete dahil edilmez.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from numpy.typing import NDArray

from sinek.connectome.connectome import Connectome, NeuronIndex

_UNASSIGNED = "None"


@dataclass(frozen=True, eq=False)
class NeuropilMap:
    names: tuple[str, ...]
    counts: sp.csr_array  # (nöron, nöropil): çıkış sinapsı sayısı

    def activity(self, rates_hz: NDArray[np.floating]) -> pd.Series:
        """Nöropil başına sinaptik olay/sn, büyükten küçüğe sıralı."""
        events = self.counts.T @ np.asarray(rates_hz, dtype=np.float64)
        return pd.Series(events, index=list(self.names), name="sinaptik_olay_hz").sort_values(
            ascending=False
        )

    def mean_rate(self, rates_hz: NDArray[np.floating]) -> pd.Series:
        """Nöropil başına sinaps ağırlıklı ortalama ateşleme hızı (Hz), ad sırasıyla."""
        events = self.counts.T @ np.asarray(rates_hz, dtype=np.float64)
        synapses = np.asarray(self.counts.sum(axis=0)).ravel()
        mean = np.divide(events, synapses, out=np.zeros_like(events), where=synapses > 0)
        return pd.Series(mean, index=list(self.names), name="ortalama_hiz_hz")


def load_neuropil_map(path: Path, connectome: Connectome | NeuronIndex) -> NeuropilMap:
    table = pd.read_feather(path, columns=["pre_pt_root_id", "neuropil", "count"])
    table = table[table["neuropil"] != _UNASSIGNED]
    indices, _ = connectome.index_of(table["pre_pt_root_id"].to_numpy(dtype=np.int64))
    in_model = np.isin(table["pre_pt_root_id"].to_numpy(dtype=np.int64), connectome.flywire_ids)
    table = table[in_model]

    names = tuple(sorted(table["neuropil"].unique()))
    column = pd.Categorical(table["neuropil"], categories=names).codes.astype(np.int64)
    counts = sp.coo_array(
        (table["count"].to_numpy(dtype=np.float64), (indices, column)),
        shape=(connectome.n_neurons, len(names)),
    ).tocsr()
    counts.sum_duplicates()
    return NeuropilMap(names=names, counts=counts)
