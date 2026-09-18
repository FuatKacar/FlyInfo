"""PyTorch LIF modelinin referans Brian2 modeliyle denkliği.

Deterministik testler (Poisson girdisi yok): spike trenleri BİREBİR aynı olmalı.
Stokastik testler: ateşleme hızları istatistiksel olarak uyumlu olmalı.
"""

import numpy as np
import pytest
import scipy.sparse as sp
import torch

from sinek.connectome.connectome import Connectome, SignSource
from sinek.simulation.lif import Stimulus, simulate
from sinek.simulation.params import LIFParams

from .brian2_reference import run_brian2

pytest.importorskip("brian2")

CPU = torch.device("cpu")


Network = tuple[Connectome, np.ndarray, np.ndarray, np.ndarray]  # type: ignore[type-arg]


def random_network(
    n: int, density: float, seed: int, excitatory: float = 0.7, max_count: int = 200
) -> Network:
    rng = np.random.default_rng(seed)
    mask = rng.random((n, n)) < density
    np.fill_diagonal(mask, False)
    pre, post = np.nonzero(mask)
    counts = rng.integers(1, max_count, size=pre.size)
    signs = np.where(rng.random(n) < excitatory, 1, -1)[pre]  # işaret presinaptik nörona bağlı
    signed = counts * signs
    weights = sp.coo_array((signed.astype(np.float32), (post, pre)), shape=(n, n)).tocsr()
    connectome = Connectome(
        flywire_ids=np.arange(n, dtype=np.int64), weights=weights, sign_source=SignSource.REFERENCE
    )
    return connectome, pre, post, signed


def as_spike_set(spikes: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]
    order = np.lexsort((spikes[:, 0], spikes[:, 1]))
    return spikes[order]


# (yoğunluk, uyarıcı oranı, en büyük sinaps sayısı, tohum): kısa süreli ve 300 ms boyunca
# kendini sürdüren aktivite rejimleri; refrakter dönemde gelen girdiler sık görülür.
REGIMES = [(0.05, 0.7, 200, 2), (0.05, 0.7, 200, 3), (0.08, 0.6, 150, 3), (0.08, 0.6, 150, 7)]


@pytest.mark.parametrize(("density", "excitatory", "max_count", "seed"), REGIMES)
def test_deterministik_ag_spike_trenleri_birebir_ayni(
    density: float, excitatory: float, max_count: int, seed: int
) -> None:
    n = 120
    connectome, pre, post, signed = random_network(n, density, seed, excitatory, max_count)
    params = LIFParams(t_run_ms=300.0, n_trials=1)
    rng = np.random.default_rng(100 + seed)
    initial_v = rng.uniform(-52.0, -38.0, size=n)  # bir kısmı eşiğin üstünde başlar

    reference = run_brian2(n, pre, post, signed, params, initial_v_mv=initial_v)
    ours = simulate(
        connectome, [], params=params, device=CPU, record_spikes=True, initial_v_mv=initial_v
    )

    assert ours.spikes is not None
    ours_spikes = as_spike_set(ours.spikes[:, 1:])
    assert len(reference.spikes) > 100, "test ağı yeterince aktif değil"
    np.testing.assert_array_equal(ours_spikes, reference.spikes)


def test_susturma_referansla_birebir_ayni() -> None:
    n = 120
    connectome, pre, post, signed = random_network(n, 0.08, 7, excitatory=0.6, max_count=150)
    params = LIFParams(t_run_ms=300.0, n_trials=1)
    initial_v = np.random.default_rng(107).uniform(-52.0, -38.0, size=n)
    silenced = [0, 5, 11, 42]

    reference = run_brian2(n, pre, post, signed, params, silenced=silenced, initial_v_mv=initial_v)
    ours = simulate(
        connectome,
        [],
        params=params,
        silenced=silenced,
        device=CPU,
        record_spikes=True,
        initial_v_mv=initial_v,
    )
    baseline = simulate(connectome, [], params=params, device=CPU, initial_v_mv=initial_v)

    assert ours.spikes is not None
    np.testing.assert_array_equal(as_spike_set(ours.spikes[:, 1:]), reference.spikes)
    assert not np.array_equal(ours.spike_counts, baseline.spike_counts), "susturma etkisiz"


def test_poisson_uyarimi_istatistiksel_olarak_uyumlu() -> None:
    """Bağlantısız nöronlarda Poisson sürümlü ateşleme hızı referansla aynı dağılımda olmalı."""
    n, rate = 200, 150.0
    empty = sp.csr_array((n, n), dtype=np.float32)
    connectome = Connectome(
        flywire_ids=np.arange(n, dtype=np.int64), weights=empty, sign_source=SignSource.REFERENCE
    )
    params = LIFParams(t_run_ms=1000.0, n_trials=1)
    targets = np.arange(n, dtype=np.int64)

    reference = run_brian2(
        n,
        np.empty(0, np.int64),
        np.empty(0, np.int64),
        np.empty(0, np.int64),
        params,
        poisson=[(targets.tolist(), rate)],
        seed=1,
    )
    ours = simulate(connectome, [Stimulus(targets, rate)], params=params, device=CPU, seed=1)

    ref_mean, our_mean = reference.counts.mean(), ours.spike_counts[0].mean()
    pooled_se = np.sqrt(reference.counts.var() / n + ours.spike_counts[0].var() / n)
    assert abs(ref_mean - our_mean) < 4 * pooled_se
    # Beklenen: her Poisson olayı bir sonraki adımda spike üretir, ~rate'e yakın
    assert 0.9 * rate < our_mean < rate
