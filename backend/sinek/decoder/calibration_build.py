"""Çözümleyici kalibrasyonunun hazır senaryo paketinden üretilmesi.

Bir davranışın referans hızı, tek kategorili senaryolar arasında o davranışın okuma nöronlarında
gözlenen en yüksek hızdır. Bu en yüksek hız etkinlik eşiğini geçmiyorsa (hiçbir doğal uyarım o
davranışı başlatmıyorsa) referans tanımsız bırakılır ve skor üretilmez.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from sinek.connectome.download import sha256_of
from sinek.connectome.groups import DEFAULT_GROUPS_PATH, Behavior
from sinek.connectome.pipeline import DataBundle
from sinek.decoder.decoder import CALIBRATION_PATH, _strongest, is_active, readout_groups
from sinek.simulation.precompute import PACKAGE_VERSION, load_result
from sinek.simulation.scenarios import Scenario, scenario_set


def build_calibration(
    bundle: DataBundle, package_dir: Path, output: Path = CALIBRATION_PATH
) -> dict[str, object]:
    n = bundle.connectome.n_neurons
    singles: list[Scenario] = [s for s in scenario_set() if len(s.components) == 1]
    readouts = readout_groups(bundle.groups)

    best: dict[Behavior, tuple[float, float, str, str]] = {}
    n_trials: set[int] = set()
    for scenario in singles:
        result = load_result(package_dir / f"{scenario.key}.npz", scenario)
        n_trials.add(result.n_trials)
        rates, stds = result.rates_hz(n), result.rates_std_hz(n)
        for behavior, candidates in readouts.items():
            group, index = _strongest(candidates, rates)
            rate = float(rates[index])
            if behavior not in best or rate > best[behavior][0]:
                best[behavior] = (rate, float(stds[index]), scenario.key, group.definition.key)

    if len(n_trials) != 1:
        raise ValueError(f"Senaryolar farklı deneme sayılarıyla üretilmiş: {n_trials}")
    (trials,) = n_trials

    behaviors = {}
    for behavior in Behavior:
        rate, std, scenario_key, group_key = best[behavior]
        calibrated = is_active(rate, std, trials)
        behaviors[behavior.value] = {
            "reference_rate_hz": round(rate, 6) if calibrated else None,
            "reference_scenario": scenario_key if calibrated else None,
            "reference_group": group_key if calibrated else None,
            "max_observed_rate_hz": round(rate, 6),
            "max_observed_scenario": scenario_key,
        }

    data: dict[str, object] = {
        "schema_version": 1,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "package_version": PACKAGE_VERSION,
        "neuron_groups_sha256": sha256_of(DEFAULT_GROUPS_PATH),
        "n_trials": trials,
        "scenario_files_sha256": {s.key: sha256_of(package_dir / f"{s.key}.npz") for s in singles},
        "rule": "referans = tek kategorili senaryolarda okuma nöronlarının en yüksek hızı",
        "behaviors": behaviors,
    }
    output.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return data
