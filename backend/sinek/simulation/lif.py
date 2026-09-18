"""Tam beyin sızıntılı birleştir-ateşle (LIF) simülasyonu, PyTorch.

Shiu et al. (2024) Brian2 modelinin adım adım aynı semantikle yeniden uygulamasıdır.
Tüm denemeler tek bir toplu (batch) tensörde paralel çalışır.

Nöron denklemleri (Brian2, `unless refractory`):
    dv/dt = (v_0 - v + g) / t_mbr
    dg/dt = -g / tau

Her zaman adımında Brian2 çizelgesinin sırası korunur:
    1. groups     : not_refractory güncellenir; refrakter olmayanlarda v, g analitik ilerletilir
    2. thresholds : spike = (v > v_th) ve not_refractory; spike atan refrakter olur
    3. synapses   : gecikmesi dolan spike'lar g'ye eklenir (g += w), Poisson girdisi v'ye eklenir.
                    `unless refractory` değişkenlerine yazma koşulludur: refrakter nörona gelen
                    girdi yok sayılır (Brian2 conditional write).
    4. resets     : spike atanlarda v = v_rst, g = 0

Susturma, referans koddaki gibi susturulan nöronların ÇIKIŞ sinapslarını sıfırlar.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import torch
from numpy.typing import NDArray

from sinek.connectome.connectome import Connectome
from sinek.simulation.params import LIFParams

ProgressCallback = Callable[[int, int], None]

_NEVER_SPIKED = -(10**9)


@dataclass(frozen=True)
class Stimulus:
    """Bir nöron grubuna sabit frekanslı Poisson girdisi (optogenetik aktivasyon modeli)."""

    indices: NDArray[np.int64]
    rate_hz: float

    def __post_init__(self) -> None:
        if self.rate_hz < 0:
            raise ValueError("Uyarım frekansı negatif olamaz")


@dataclass(frozen=True)
class SimulationResult:
    spike_counts: NDArray[np.int32]  # (deneme, nöron)
    params: LIFParams
    seed: int
    spikes: NDArray[np.int64] | None = field(default=None)  # (k, 3): deneme, nöron, adım

    @property
    def rates_hz(self) -> NDArray[np.float64]:
        """Deneme ortalaması ateşleme hızı (referans `utils.get_rate` ile aynı tanım)."""
        return self.spike_counts.mean(axis=0) / (self.params.t_run_ms / 1000.0)

    @property
    def rates_std_hz(self) -> NDArray[np.float64]:
        """Denemeler arası standart sapma (numpy varsayılanı ddof=0, referansla aynı)."""
        return self.spike_counts.std(axis=0) / (self.params.t_run_ms / 1000.0)


def default_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class _OutgoingSynapses:
    """Presinaptik nörona göre (CSC) düzenlenmiş işaretli ağırlıklar."""

    def __init__(
        self,
        connectome: Connectome,
        silenced: NDArray[np.int64],
        w_syn_mv: float,
        device: torch.device,
        dtype: torch.dtype,
    ) -> None:
        csc = connectome.weights.tocsc()
        csc.sort_indices()
        weights = csc.data.astype(np.float64) * w_syn_mv
        if silenced.size:
            ptr = csc.indptr
            for pre in np.unique(silenced):
                weights[ptr[pre] : ptr[pre + 1]] = 0.0
        self.col_ptr = torch.as_tensor(csc.indptr.astype(np.int64), device=device)
        self.post = torch.as_tensor(csc.indices.astype(np.int64), device=device)
        self.weight = torch.as_tensor(weights, dtype=dtype, device=device)

    def targets(
        self, trial: torch.Tensor, pre: torch.Tensor, n_neurons: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Spike atan (deneme, nöron) çiftleri için düz hedef indeksleri ve ağırlıkları."""
        starts = self.col_ptr[pre]
        counts = self.col_ptr[pre + 1] - starts
        total = int(counts.sum())
        if total == 0:
            empty = torch.empty(0, dtype=torch.int64, device=pre.device)
            return empty, self.weight[:0]
        offsets = torch.cumsum(counts, 0) - counts
        local = torch.arange(total, device=pre.device) - torch.repeat_interleave(offsets, counts)
        edge = torch.repeat_interleave(starts, counts) + local
        flat = torch.repeat_interleave(trial, counts) * n_neurons + self.post[edge]
        return flat, self.weight[edge]


def simulate(
    connectome: Connectome,
    stimuli: Sequence[Stimulus],
    *,
    params: LIFParams | None = None,
    silenced: Sequence[int] | NDArray[np.int64] = (),
    seed: int = 0,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float64,
    record_spikes: bool = False,
    initial_v_mv: NDArray[np.float64] | None = None,
    progress: ProgressCallback | None = None,
) -> SimulationResult:
    """Uyarım ve susturma deneyini tüm denemeler için paralel çalıştırır.

    `initial_v_mv` yalnızca testler içindir (referansla deterministik karşılaştırma).
    """
    p = params or LIFParams()
    device = device or default_device()
    n = connectome.n_neurons
    b = p.n_trials

    generator = torch.Generator(device=device).manual_seed(seed)
    silenced_idx = np.asarray(silenced, dtype=np.int64)
    synapses = _OutgoingSynapses(connectome, silenced_idx, p.w_syn_mv, device, dtype)

    # Analitik (kesin) doğrusal çözüm: g üstel söner, u = v - v_0 iki üstelin toplamıdır.
    decay_m = math.exp(-p.dt_ms / p.t_mbr_ms)
    decay_s = math.exp(-p.dt_ms / p.tau_ms)
    coupling = p.tau_ms / (p.tau_ms - p.t_mbr_ms)

    v = torch.full((b, n), p.v_0_mv, dtype=dtype, device=device)
    if initial_v_mv is not None:
        v[:] = torch.as_tensor(initial_v_mv, dtype=dtype, device=device)
    g = torch.zeros((b, n), dtype=dtype, device=device)
    last_spike = torch.full((b, n), _NEVER_SPIKED, dtype=torch.int64, device=device)
    counts = torch.zeros((b, n), dtype=torch.int32, device=device)

    refractory_steps = torch.full((n,), p.refractory_steps, dtype=torch.int64, device=device)
    stim_index: list[torch.Tensor] = []
    stim_prob: list[float] = []
    for stimulus in stimuli:
        idx = torch.as_tensor(np.asarray(stimulus.indices, dtype=np.int64), device=device)
        refractory_steps[idx] = 0  # referans: Poisson hedeflerinin refrakter dönemi yok
        stim_index.append(idx)
        stim_prob.append(stimulus.rate_hz * p.dt_ms / 1000.0)

    delay = p.delay_steps
    queue = torch.zeros((max(delay, 1), b, n), dtype=torch.bool, device=device)
    recorded: list[torch.Tensor] = []

    for step in range(p.n_steps):
        # 1. groups
        not_refractory = (step - last_spike) >= refractory_steps
        mask = not_refractory.to(dtype)
        u = v - p.v_0_mv
        a = g * coupling
        v = torch.where(not_refractory, p.v_0_mv + (u - a) * decay_m + a * decay_s, v)
        g = g - g * (1.0 - decay_s) * mask

        # 2. thresholds
        spikes = (v > p.v_th_mv) & not_refractory
        last_spike = torch.where(spikes, step, last_spike)
        not_refractory = not_refractory & ~spikes
        mask = not_refractory.to(dtype)

        # 3. synapses (gecikme 0 ise spike aynı adımda iletilir)
        slot = step % queue.shape[0]
        if delay == 0:
            queue[slot] = spikes
        due = queue[slot].nonzero()
        if due.numel():
            flat, weight = synapses.targets(due[:, 0], due[:, 1], n)
            g_flat = g.view(-1)
            g_flat.index_add_(0, flat, weight * mask.view(-1)[flat])
        if delay > 0:
            queue[slot] = spikes

        for idx, prob in zip(stim_index, stim_prob, strict=True):
            if prob <= 0:
                continue
            draws = torch.rand((b, idx.numel()), generator=generator, device=device, dtype=dtype)
            kick = (draws < prob).to(dtype) * p.poisson_weight_mv * mask[:, idx]
            v.index_add_(1, idx, kick)

        # 4. resets
        v = torch.where(spikes, p.v_rst_mv, v)
        g = torch.where(spikes, 0.0, g)

        counts += spikes.to(torch.int32)
        if record_spikes and spikes.any():
            hit = spikes.nonzero()
            recorded.append(torch.cat([hit, torch.full_like(hit[:, :1], step)], dim=1))
        if progress and (step + 1) % 100 == 0:
            progress(step + 1, p.n_steps)

    spike_array = None
    if record_spikes:
        spike_array = (
            torch.cat(recorded).cpu().numpy() if recorded else np.empty((0, 3), dtype=np.int64)
        )
    return SimulationResult(
        spike_counts=counts.cpu().numpy(), params=p, seed=seed, spikes=spike_array
    )
