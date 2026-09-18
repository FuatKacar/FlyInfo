"""Önceden hesaplanan uyarım senaryoları.

Yoğunluk (0–1) frekansa doğrusal eşlenir: frekans = yoğunluk × F_MAX_HZ.
F_MAX_HZ = 200 Hz, Shiu et al. (2024) şekil 1D ve 3A'daki en yüksek uyarım frekansıdır.

Senaryo seti:
    - kontrol (uyarımsız) × 1
    - tek kategori × 5 yoğunluk
    - kategori çiftleri × 3 × 3 yoğunluk (tekli yoğunlukların alt kümesi)
"""

from dataclasses import dataclass
from itertools import combinations

F_MAX_HZ = 200.0
INTENSITY_LEVELS: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8, 1.0)
PAIR_INTENSITY_LEVELS: tuple[float, ...] = (0.2, 0.6, 1.0)

# Sohbet sekmesinin uyarım kategorileri (neuron_groups.toml anahtarları)
CHAT_CATEGORIES: tuple[str, ...] = (
    "sugar",
    "bitter",
    "water",
    "johnston_organ",
    "looming",
    "geosmin",
    "co2",
)


@dataclass(frozen=True)
class Scenario:
    components: tuple[tuple[str, float], ...]  # (grup anahtarı, yoğunluk), anahtara göre sıralı

    @property
    def key(self) -> str:
        if not self.components:
            return "kontrol"
        return "+".join(f"{group}@{intensity:.1f}" for group, intensity in self.components)

    @property
    def stimuli_hz(self) -> tuple[tuple[str, float], ...]:
        return tuple((group, intensity * F_MAX_HZ) for group, intensity in self.components)


def make_scenario(*components: tuple[str, float]) -> Scenario:
    groups = [group for group, _ in components]
    if len(set(groups)) != len(groups):
        raise ValueError("Bir senaryoda aynı grup iki kez kullanılamaz")
    for _, intensity in components:
        if not 0.0 < intensity <= 1.0:
            raise ValueError("Yoğunluk (0, 1] aralığında olmalı")
        # Anahtar yoğunluğu tek ondalıkla yazar; daha ince değerler başka senaryoyla çakışırdı.
        if round(intensity, 1) != intensity:
            raise ValueError("Yoğunluk 0,1'lik adımlarla verilmeli")
    return Scenario(tuple(sorted(components)))


def scenario_set(categories: tuple[str, ...] = CHAT_CATEGORIES) -> tuple[Scenario, ...]:
    singles = [make_scenario((c, i)) for c in categories for i in INTENSITY_LEVELS]
    pairs = [
        make_scenario((a, i), (b, j))
        for a, b in combinations(categories, 2)
        for i in PAIR_INTENSITY_LEVELS
        for j in PAIR_INTENSITY_LEVELS
    ]
    return (Scenario(()), *singles, *pairs)
