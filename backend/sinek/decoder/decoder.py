"""Deterministik davranış çözümleyicisi.

Her davranış, literatürde o davranışla nedensel ilişkisi gösterilmiş okuma nöronlarından okunur
(neuron_groups.toml, role = "readout"). Kurallar docs/cozumleyici.md'de gerekçeleriyle yazılıdır:

    okuma hızı   = davranışın okuma grupları içindeki nöronların EN YÜKSEK ateşleme hızı
                   (tek taraflı uyarımlar yalnızca bir yarıküredeki komut nöronunu etkinleştirir)
    etkin        = hız ≥ MIN_ACTIVE_RATE_HZ  ve  hız - 2·SE > 0   (SE = std / √(n - 1))
    skor         = min(hız / kalibrasyon referansı, 1); referans yoksa None
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from sinek.connectome.groups import Behavior, GroupRole, ResolvedGroup
from sinek.connectome.neuropils import NeuropilMap
from sinek.decoder.schema import (
    BehaviorReadout,
    DecoderOutput,
    ModelInfo,
    NeuropilActivity,
    StimulusInfo,
)

MIN_ACTIVE_RATE_HZ = 5.0
SIGNIFICANCE_SE = 2.0
TOP_NEUROPILS = 5
CALIBRATION_PATH = Path(__file__).with_name("calibration.json")


@dataclass(frozen=True)
class BehaviorCalibration:
    reference_rate_hz: float | None  # None: hiçbir doğal uyarım bu davranışı etkinleştirmedi
    reference_scenario: str | None
    reference_group: str | None


def readout_groups(groups: dict[str, ResolvedGroup]) -> dict[Behavior, list[ResolvedGroup]]:
    result: dict[Behavior, list[ResolvedGroup]] = {b: [] for b in Behavior}
    for group in groups.values():
        d = group.definition
        if d.role is GroupRole.READOUT and d.behavior is not None:
            result[d.behavior].append(group)
    return result


def _strongest(
    candidates: list[ResolvedGroup], rates: NDArray[np.float64]
) -> tuple[ResolvedGroup, int]:
    """En yüksek hızlı nöronu ve grubunu döndürür (eşitlikte tanım sırası korunur)."""
    best_group, best_index, best_rate = candidates[0], int(candidates[0].indices[0]), -1.0
    for group in candidates:
        for index in group.indices:
            if rates[index] > best_rate:
                best_group, best_index, best_rate = group, int(index), float(rates[index])
    return best_group, best_index


def is_active(rate_hz: float, std_hz: float, n_trials: int) -> bool:
    se = float(std_hz) / float(np.sqrt(max(n_trials - 1, 1)))
    return bool(rate_hz >= MIN_ACTIVE_RATE_HZ and rate_hz - SIGNIFICANCE_SE * se > 0)


def load_calibration(path: Path = CALIBRATION_PATH) -> dict[Behavior, BehaviorCalibration]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        Behavior(key): BehaviorCalibration(
            reference_rate_hz=value["reference_rate_hz"],
            reference_scenario=value["reference_scenario"],
            reference_group=value["reference_group"],
        )
        for key, value in data["behaviors"].items()
    }


def decode(
    rates_hz: NDArray[np.float64],
    rates_std_hz: NDArray[np.float64],
    groups: dict[str, ResolvedGroup],
    stimulus: StimulusInfo,
    model: ModelInfo,
    calibration: dict[Behavior, BehaviorCalibration],
    neuropils: NeuropilMap | None,
) -> DecoderOutput:
    behaviors = []
    for behavior, candidates in readout_groups(groups).items():
        group, index = _strongest(candidates, rates_hz)
        rate, std = float(rates_hz[index]), float(rates_std_hz[index])
        reference = calibration[behavior].reference_rate_hz
        score = None if reference is None else min(rate / reference, 1.0)
        behaviors.append(
            BehaviorReadout(
                behavior=behavior,
                readout_group=group.definition.key,
                rate_hz=rate,
                rate_std_hz=std,
                score=score,
                active=is_active(rate, std, model.n_trials),
            )
        )

    # Laboratuvar uyarımlarında bileşen anahtarı hazır bir gruba karşılık gelmeyebilir
    # (ör. hücre tipi seçimi); bilinmeyen bileşen varsa "yalnızca devre" iddiası yapılmaz.
    known = [groups[c.group].definition for c in stimulus.components if c.group in groups]
    circuit_only = (
        bool(stimulus.components)
        and len(known) == len(stimulus.components)
        and all(d.circuit_only for d in known)
    )

    top: list[NeuropilActivity] = []
    if neuropils is not None:
        activity = neuropils.activity(rates_hz)
        total = float(activity.sum())
        if total > 0:
            top = [
                NeuropilActivity(neuropil=name, events_hz=float(value), share=float(value / total))
                for name, value in activity.head(TOP_NEUROPILS).items()
                if value > 0
            ]

    return DecoderOutput(
        stimulus=stimulus,
        behaviors=tuple(behaviors),
        circuit_only=circuit_only,
        top_neuropils=tuple(top),
        active_neuron_count=int((rates_hz > 0).sum()),
        model=model,
    )
