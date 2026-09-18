"""Sinyal yolu izleme: uyarılan nöronlardan bir okuma nöronuna giden en güçlü yollar.

**Yöntem.** Bir kenarın (u → v) gücü, u'nun v'ye saniyede ilettiği sinaptik olayın, v'ye gelen tüm
olaylar içindeki payıdır:

    pay(u → v) = sinaps(u, v) × hız(u)  /  Σ_w sinaps(w, v) × hız(w)

Hızlar simülasyondan gelir; hiç ateşlemeyen nöronlar hesaba girmez. Bir yolun gücü, üzerindeki
kenar paylarının çarpımıdır (0–1). Yolun işareti, kenar işaretlerinin çarpımıdır: çift sayıda
baskılayıcı kenar uyarıcı bir yol oluşturur.

**Sınırlılık.** Bu ölçü yapısal ve korelasyoneldir; nedensellik kanıtı değildir. Bir yolun gerçekten
gerekli olup olmadığı ancak susturma deneyiyle sınanır. Bu not arayüzde yolların yanında gösterilir.

Arama hedeften geriye doğru, ışın (beam) genişliği sınırlı yapılır: her adımda yalnızca en güçlü
`BEAM_WIDTH` kısmi yol tutulur. Bu, en güçlü yolların bulunmasını pratikte garanti eder ve tam
beyin ölçeğinde saniyeler içinde sonuçlanır.
"""

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from sinek.connectome.connectome import Connectome

MAX_HOPS = 4
BEAM_WIDTH = 400
MIN_EDGE_SHARE = 0.005  # payı binde 5'in altındaki kenarlar yol olarak anlamsız


class PathwayError(ValueError):
    """Yol analizi yapılamıyor (hedef sessiz, uyarım yok vb.)."""


class PathEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pre_id: str  # FlyWire kimliği (JavaScript hassasiyeti için metin)
    post_id: str
    pre_cell_type: str | None = None  # FlyWire anotasyonundaki hücre tipi (okunabilir ad)
    post_cell_type: str | None = None
    synapses: int
    excitatory: bool
    pre_rate_hz: float
    share: float = Field(ge=0, le=1)  # hedefe gelen olaylar içindeki payı


class Pathway(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edges: list[PathEdge]
    strength: float = Field(gt=0, le=1)
    excitatory: bool  # kenar işaretlerinin çarpımı
    hops: int


@dataclass(frozen=True)
class _Partial:
    node: int
    score: float
    sign: int
    # (pre, post, sinaps sayısı, işaret, pre hızı, pay)
    edges: tuple[tuple[int, int, int, int, float, float], ...]


def _incoming(weights: sp.csr_array, node: int) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    start, end = weights.indptr[node], weights.indptr[node + 1]
    return weights.indices[start:end].astype(np.int64), weights.data[start:end].astype(np.float64)


def strongest_paths(
    connectome: Connectome,
    rates_hz: NDArray[np.float64],
    sources: NDArray[np.int64],
    target: int,
    top_k: int = 5,
    max_hops: int = MAX_HOPS,
) -> list[Pathway]:
    """Kaynaklardan hedefe giden en güçlü yollar (hedeften geriye ışın araması)."""
    if rates_hz[target] <= 0:
        raise PathwayError("Hedef nöron bu deneyde hiç ateşlemedi; izlenecek yol yok")
    source_set = {int(i) for i in sources}
    weights = connectome.weights  # (post, pre) işaretli sinaps sayısı
    ids = connectome.flywire_ids

    beam = [_Partial(node=target, score=1.0, sign=1, edges=())]
    complete: list[_Partial] = []
    for _hop in range(max_hops):
        candidates: list[_Partial] = []
        for partial in beam:
            pre, data = _incoming(weights, partial.node)
            if pre.size == 0:
                continue
            events = np.abs(data) * rates_hz[pre]
            total = float(events.sum())
            if total <= 0:
                continue
            shares = events / total
            keep = np.flatnonzero(shares >= MIN_EDGE_SHARE)
            visited = {edge[1] for edge in partial.edges} | {partial.node}
            for index in keep:
                source = int(pre[index])
                if source in visited:  # döngüye girme
                    continue
                share = float(shares[index])
                sign = 1 if data[index] > 0 else -1
                edge = (
                    source,
                    partial.node,
                    int(abs(data[index])),
                    sign,
                    float(rates_hz[source]),
                    share,
                )
                candidates.append(
                    _Partial(
                        node=source,
                        score=partial.score * share,
                        sign=partial.sign * sign,
                        edges=(edge, *partial.edges),
                    )
                )
        if not candidates:
            break
        candidates.sort(key=lambda p: -p.score)
        beam = []
        for candidate in candidates[:BEAM_WIDTH]:
            if candidate.node in source_set:
                complete.append(candidate)
            else:
                beam.append(candidate)
        if not beam:
            break

    complete.sort(key=lambda p: -p.score)
    return [
        Pathway(
            edges=[
                PathEdge(
                    pre_id=str(ids[pre]),
                    post_id=str(ids[post]),
                    synapses=synapses,
                    excitatory=sign > 0,
                    pre_rate_hz=round(pre_rate, 3),
                    share=round(share, 6),
                )
                for pre, post, synapses, sign, pre_rate, share in path.edges
            ],
            strength=path.score,
            excitatory=path.sign > 0,
            hops=len(path.edges),
        )
        for path in complete[:top_k]
    ]
