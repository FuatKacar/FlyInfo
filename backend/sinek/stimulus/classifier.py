"""Türkçe uyarım sınıflandırıcısı (sürüm 2): deterministik kural katmanı.

Sürüm 1'de kullanılan vektör temsili (bge-m3 kNN) yedek katmanı, sürüm 2'de iki geliştirme
setinin birleşiminde yapılan bir-dışarıda çapraz doğrulamada her eşikte makro F1'i düşürdüğü
için kaldırılmıştır (docs/siniflandirma.md, "Sürüm 2"). Böylece sınıflandırma ek model
indirmesi gerektirmez, anlıktır ve her kararı kanıt kaydıyla açıklanabilir.
"""

from dataclasses import dataclass

from sinek.stimulus.rules import Evidence, classify_rules

CLASSIFIER_VERSION = "2"


@dataclass(frozen=True)
class Classification:
    levels: dict[str, int]  # kategori → yoğunluk düzeyi (1–3); boşsa kapsam dışı
    evidence: tuple[Evidence, ...]
    out_of_scope_reason: str | None

    @property
    def in_scope(self) -> bool:
        return bool(self.levels)


def classify(text: str) -> Classification:
    result = classify_rules(text)
    return Classification(result.levels, result.evidence, result.out_of_scope_reason)
