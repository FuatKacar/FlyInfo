"""Sınıflandırıcı çıktısı → uyarım senaryosu.

Yoğunluk düzeyleri (docs/siniflandirma.md, bölüm 3) hazır senaryo ızgarasının tekli ve ikili
senaryolarda ORTAK olan yoğunluklarına eşlenir. Böylece aynı ifade ("biraz bal") tek başına da
başka bir uyarıcıyla birlikte de aynı frekansla uyarılır:

    1 (hafif)  → 0,2  (40 Hz)
    2 (orta)   → 0,6  (120 Hz)
    3 (güçlü)  → 1,0  (200 Hz)

Üç veya daha fazla kategori içeren mesajların senaryosu hazır pakette yoktur; canlı simüle edilir.
"""

from sinek.simulation.scenarios import PAIR_INTENSITY_LEVELS, Scenario, make_scenario

LEVEL_INTENSITY: dict[int, float] = {1: 0.2, 2: 0.6, 3: 1.0}

assert set(LEVEL_INTENSITY.values()) <= set(PAIR_INTENSITY_LEVELS)


def scenario_for_levels(levels: dict[str, int]) -> Scenario:
    """Kategori → düzey sözlüğünden senaryo; boş sözlük kontrol (uyarımsız) senaryosudur."""
    try:
        components = [(category, LEVEL_INTENSITY[level]) for category, level in levels.items()]
    except KeyError as error:
        raise ValueError(f"Geçersiz yoğunluk düzeyi: {error.args[0]}") from None
    return make_scenario(*components)
