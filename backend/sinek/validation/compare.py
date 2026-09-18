"""İki bağımsız deney setinin (bizim model / referans) ateşleme hızlarının karşılaştırılması.

Her iki taraf da `n_trials` denemenin ortalamasını ve ddof=0 standart sapmasını raporlar.
Ortalamanın standart hatası: SE = std / sqrt(n - 1). Fark için Welch z skoru kullanılır.
Aynı model ve aynı veriyle, farklı rastgele tohumlarla üretilen sonuçlarda |z| dağılımı
yaklaşık standart normal olmalıdır (|z| < 3 oranı ≈ %99,7).
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def z_scores(
    mean_a: FloatArray, std_a: FloatArray, mean_b: FloatArray, std_b: FloatArray, n_trials: int
) -> FloatArray:
    se = np.sqrt((std_a**2 + std_b**2) / (n_trials - 1))
    diff = mean_a - mean_b
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(se > 0, diff / se, np.where(diff == 0, 0.0, np.inf))
    return z.astype(np.float64)


@dataclass(frozen=True)
class WholeBrainComparison:
    n_active: int  # herhangi bir tarafta ateşleyen nöron sayısı
    pearson_r: float
    slope: float  # orijinden geçen en küçük kareler eğimi (bizim / referans)
    within_3se: float  # |z| < 3 oranı
    n_beyond_5se: int
    max_abs_diff_hz: float
    total_rate_ours: float
    total_rate_reference: float


def compare_whole_brain(
    ours_mean: FloatArray,
    ours_std: FloatArray,
    ref_mean: FloatArray,
    ref_std: FloatArray,
    n_trials: int,
    comparable: NDArray[np.bool_] | None = None,
) -> WholeBrainComparison:
    """`comparable`: karşılaştırmaya girebilecek nöronlar (ör. iki veri sürümünde ortak olanlar)."""
    active = (ours_mean > 0) | (ref_mean > 0)
    if comparable is not None:
        active &= comparable
    a, b = ours_mean[active], ref_mean[active]
    z = z_scores(a, ours_std[active], b, ref_std[active], n_trials)
    return WholeBrainComparison(
        n_active=int(active.sum()),
        pearson_r=float(np.corrcoef(a, b)[0, 1]) if active.sum() > 1 else float("nan"),
        slope=float((a @ b) / (b @ b)) if (b @ b) > 0 else float("nan"),
        within_3se=float((np.abs(z) < 3).mean()) if active.any() else float("nan"),
        n_beyond_5se=int((np.abs(z) > 5).sum()),
        max_abs_diff_hz=float(np.abs(a - b).max()) if active.any() else 0.0,
        total_rate_ours=float(a.sum()),
        total_rate_reference=float(b.sum()),
    )


@dataclass(frozen=True)
class SingleNeuronComparison:
    ours_hz: float
    ours_std: float
    reference_hz: float
    reference_std: float
    z: float


def compare_single(
    ours_mean: float, ours_std: float, ref_mean: float, ref_std: float, n_trials: int
) -> SingleNeuronComparison:
    z = z_scores(
        np.array([ours_mean]),
        np.array([ours_std]),
        np.array([ref_mean]),
        np.array([ref_std]),
        n_trials,
    )[0]
    return SingleNeuronComparison(ours_mean, ours_std, ref_mean, ref_std, float(z))
