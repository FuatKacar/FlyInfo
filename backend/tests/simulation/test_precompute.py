import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from sinek.connectome.connectome import build_connectome, load_annotations
from sinek.connectome.groups import resolve_group
from sinek.connectome.pipeline import DataBundle
from sinek.simulation.lif import Stimulus, simulate
from sinek.simulation.params import LIFParams
from sinek.simulation.precompute import (
    load_result,
    precompute,
    run_scenario,
    save_result,
    scenario_seed,
)
from sinek.simulation.scenarios import (
    CHAT_CATEGORIES,
    F_MAX_HZ,
    INTENSITY_LEVELS,
    PAIR_INTENSITY_LEVELS,
    make_scenario,
    scenario_set,
)
from tests.connectome.test_groups import definition

CPU = torch.device("cpu")
PARAMS = LIFParams(n_trials=5, t_run_ms=40.0)


@pytest.fixture
def bundle(mini_files: tuple[Path, Path, Path]) -> DataBundle:
    completeness, connectivity, annotations_path = mini_files
    connectome = build_connectome(completeness, connectivity)
    annotations = load_annotations(annotations_path)
    group = resolve_group(definition(key="a", ids=[1000, 1002]), connectome, annotations)
    other = resolve_group(definition(key="b", ids=[1001]), connectome, annotations)
    return DataBundle(connectome, annotations, {"a": group, "b": other})


def test_senaryo_seti_boyutu_ve_benzersizligi() -> None:
    scenarios = scenario_set()
    n = len(CHAT_CATEGORIES)
    pairs = n * (n - 1) // 2

    assert len(scenarios) == 1 + n * len(INTENSITY_LEVELS) + pairs * len(PAIR_INTENSITY_LEVELS) ** 2
    assert len({s.key for s in scenarios}) == len(scenarios)
    assert set(PAIR_INTENSITY_LEVELS) <= set(INTENSITY_LEVELS)


def test_senaryo_anahtari_bilesen_sirasindan_bagimsiz() -> None:
    a = make_scenario(("water", 0.6), ("bitter", 1.0))
    b = make_scenario(("bitter", 1.0), ("water", 0.6))

    assert a == b
    assert a.key == "bitter@1.0+water@0.6"
    assert a.stimuli_hz == (("bitter", F_MAX_HZ), ("water", 0.6 * F_MAX_HZ))


@pytest.mark.parametrize("components", [(("a", 0.0),), (("a", 1.5),), (("a", 0.2), ("a", 0.4))])
def test_gecersiz_senaryolar_reddedilir(components: tuple[tuple[str, float], ...]) -> None:
    with pytest.raises(ValueError, match=r"Yoğunluk|iki kez"):
        make_scenario(*components)


def test_saklanan_tam_sayilardan_hizlar_simulasyonla_birebir_ayni(
    bundle: DataBundle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sinek.simulation.lif.default_device", lambda: CPU)
    scenario = make_scenario(("a", 1.0))
    direct = simulate(
        bundle.connectome,
        [Stimulus(bundle.groups["a"].indices, F_MAX_HZ)],
        params=PARAMS,
        seed=scenario_seed(scenario.key),
        device=CPU,
    )

    path = tmp_path / "s.npz"
    save_result(path, run_scenario(scenario, bundle, PARAMS, device=CPU))
    loaded = load_result(path, scenario)

    n = bundle.connectome.n_neurons
    np.testing.assert_array_equal(loaded.rates_hz(n), direct.rates_hz)
    np.testing.assert_allclose(loaded.rates_std_hz(n), direct.rates_std_hz, rtol=0, atol=1e-9)


def test_hesaplama_devam_eder_ve_degisen_parametrede_yeniler(
    bundle: DataBundle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sinek.simulation.lif.default_device", lambda: CPU)
    scenarios = (make_scenario(("a", 1.0)), make_scenario(("a", 0.6), ("b", 1.0)))
    statuses: list[str] = []

    def record(_n: int, _t: int, _s: object, status: str) -> None:
        statuses.append(status)

    manifest = precompute(scenarios, bundle, tmp_path, tmp_path, PARAMS, progress=record)
    precompute(scenarios, bundle, tmp_path, tmp_path, PARAMS, progress=record)
    changed = LIFParams(n_trials=4, t_run_ms=40.0)
    precompute(scenarios, bundle, tmp_path, tmp_path, changed, progress=record)

    assert statuses[:4] == ["basliyor", "hesaplandi"] * 2
    assert statuses[4:6] == ["mevcut", "mevcut"]
    assert statuses[6:] == ["basliyor", "hesaplandi"] * 2  # parmak izi değişti

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert set(data["scenarios"]) == {s.key for s in scenarios}
    assert all(len(v["sha256"]) == 64 for v in data["scenarios"].values())
    assert pd.Series(data["params"]).loc["n_trials"] == 4
