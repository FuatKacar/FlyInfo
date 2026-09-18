import numpy as np
import pytest

from sinek.validation.compare import compare_single, compare_whole_brain, z_scores
from sinek.validation.experiments import EXPERIMENTS
from sinek.validation.run import experiment_seed


def test_z_skoru_welch_formulu() -> None:
    z = z_scores(np.array([12.0]), np.array([3.0]), np.array([10.0]), np.array([4.0]), n_trials=26)

    assert z[0] == pytest.approx(2.0 / np.sqrt((9 + 16) / 25))


def test_sifir_varyansta_z_esitse_sifir_farkliysa_sonsuz() -> None:
    z = z_scores(np.array([5.0, 5.0]), np.zeros(2), np.array([5.0, 6.0]), np.zeros(2), n_trials=30)

    assert z[0] == 0.0
    assert np.isinf(z[1])


def test_ayni_dagilimdan_orneklerde_z_standart_normal() -> None:
    """Aynı süreçten bağımsız iki deney seti: |z|<3 oranı ≈ %99,7 olmalı."""
    rng = np.random.default_rng(0)
    n_neurons, n_trials = 4000, 30
    true_rate = rng.uniform(1, 80, n_neurons)
    a = rng.poisson(true_rate, (n_trials, n_neurons))
    b = rng.poisson(true_rate, (n_trials, n_neurons))

    result = compare_whole_brain(a.mean(0), a.std(0), b.mean(0), b.std(0), n_trials)

    assert result.within_3se > 0.99
    assert result.pearson_r > 0.99
    assert result.slope == pytest.approx(1.0, abs=0.01)


def test_sistematik_sapma_yakalanir() -> None:
    rng = np.random.default_rng(1)
    true_rate = rng.uniform(5, 80, 2000)
    a = rng.poisson(true_rate * 1.15, (30, 2000))  # %15 sistematik fazla
    b = rng.poisson(true_rate, (30, 2000))

    result = compare_whole_brain(a.mean(0), a.std(0), b.mean(0), b.std(0), 30)

    assert result.within_3se < 0.9
    assert result.n_beyond_5se > 0
    assert result.slope == pytest.approx(1.15, abs=0.02)


def test_sessiz_noronlar_karsilastirmaya_katilmaz() -> None:
    ours = np.array([0.0, 0.0, 10.0])
    ref = np.array([0.0, 0.0, 10.0])

    result = compare_whole_brain(ours, np.ones(3), ref, np.ones(3), 30)

    assert result.n_active == 1


def test_tek_noron_karsilastirmasi() -> None:
    result = compare_single(67.0, 5.0, 68.2, 5.0, 30)

    assert result.z == pytest.approx(-1.2 / np.sqrt(50 / 29))


def test_deney_anahtarlari_benzersiz_ve_tohumlar_kararli() -> None:
    keys = [e.key for e in EXPERIMENTS]

    assert len(set(keys)) == len(keys)
    assert experiment_seed("fig1d_sugar_40hz") == experiment_seed("fig1d_sugar_40hz")
    assert len({experiment_seed(k) for k in keys}) == len(keys)
