"""Shiu et al. (2024) Brian2 modelinin test amaçlı birebir kopyası.

Kaynak: philshiu/Drosophila_brain_model @ 91bdd1e7, model.py (MIT lisansı).
Denklemler, eşik/sıfırlama kuralları, gecikme, refrakter dönem, Poisson girdisi ve
susturma yöntemi değiştirilmeden alınmıştır; yalnızca girdi dosya yerine dizilerden okunur
ve deterministik testler için başlangıç potansiyeli ayarlanabilir.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from textwrap import dedent

import numpy as np
from numpy.typing import NDArray

from sinek.simulation.params import LIFParams


@dataclass(frozen=True)
class Brian2Run:
    spikes: NDArray[np.int64]  # (k, 2): nöron, adım
    counts: NDArray[np.int64]  # (nöron,)


def run_brian2(
    n: int,
    pre: NDArray[np.int64],
    post: NDArray[np.int64],
    signed_counts: NDArray[np.int64],
    params: LIFParams,
    *,
    poisson: Sequence[tuple[Sequence[int], float]] = (),
    silenced: Sequence[int] = (),
    initial_v_mv: NDArray[np.float64] | None = None,
    seed: int = 0,
) -> Brian2Run:
    from brian2 import (
        Hz,
        Network,
        NeuronGroup,
        PoissonInput,
        SpikeMonitor,
        Synapses,
        defaultclock,
        ms,
        mV,
        prefs,
    )
    from brian2 import seed as brian_seed

    prefs.codegen.target = "numpy"
    defaultclock.dt = params.dt_ms * ms
    brian_seed(seed)

    namespace = {
        "v_0": params.v_0_mv * mV,
        "v_rst": params.v_rst_mv * mV,
        "v_th": params.v_th_mv * mV,
        "t_mbr": params.t_mbr_ms * ms,
        "tau": params.tau_ms * ms,
    }
    eqs = dedent("""
        dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)
        dg/dt = -g / tau               : volt (unless refractory)
        rfc                            : second
        """)
    neu = NeuronGroup(
        N=n,
        model=eqs,
        method="linear",
        threshold="v > v_th",
        reset="v = v_rst; w = 0; g = 0 * mV",
        refractory="rfc",
        name="default_neurons",
        namespace=namespace,
    )
    neu.v = params.v_0_mv * mV
    if initial_v_mv is not None:
        neu.v = initial_v_mv * mV
    neu.g = 0
    neu.rfc = params.t_rfc_ms * ms

    syn = Synapses(
        neu, neu, "w : volt", on_pre="g += w", delay=params.t_dly_ms * ms, name="default_synapses"
    )
    if pre.size:  # Brian2 boş bağlantı listesini kabul etmez
        syn.connect(i=pre, j=post)
        syn.w = signed_counts * params.w_syn_mv * mV

    inputs = []
    for targets, rate_hz in poisson:
        for i in targets:
            inputs.append(
                PoissonInput(
                    target=neu[i],
                    target_var="v",
                    N=1,
                    rate=rate_hz * Hz,
                    weight=params.poisson_weight_mv * mV,
                )
            )
            neu[i].rfc = 0 * ms

    for i in silenced:  # referans: syn.w[' {} == i'.format(i)] = 0*mV
        syn.w[f" {i} == i"] = 0 * mV

    monitor = SpikeMonitor(neu)
    net = Network(neu, monitor, *inputs)
    if pre.size:
        net.add(syn)
    net.run(duration=params.t_run_ms * ms)

    steps = np.rint(np.asarray(monitor.t / ms) / params.dt_ms).astype(np.int64)
    neurons = np.asarray(monitor.i, dtype=np.int64)
    order = np.lexsort((neurons, steps))
    spikes = np.stack([neurons[order], steps[order]], axis=1)
    return Brian2Run(spikes=spikes, counts=np.bincount(neurons, minlength=n))
