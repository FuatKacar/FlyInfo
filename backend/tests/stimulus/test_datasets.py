"""Etiketli Türkçe veri setlerinin bütünlüğü (docs/siniflandirma.md kurallarına göre)."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from sinek.simulation.scenarios import CHAT_CATEGORIES

DATA = Path(__file__).resolve().parents[2] / "sinek" / "stimulus" / "data"
ALLOWED_CHARACTERS = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9 .,;:!?'\"()%₂-]+")
KNOWN_TAGS = {
    "tekil",
    "coklu",
    "kapsam_disi",
    "olumsuz",
    "mecaz",
    "argo",
    "yazim_hatasi",
    "soru",
    "sinir",
}


def rows(name: str) -> list[dict[str, object]]:
    lines = (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


TEST_SET_SHA256 = "bf8ebdb7be9c4dfad92db90afe8a9d531afb9eea3d7ccd7aef6352d984c8ab78"
SETS = ["gelistirme", "gelistirme2", "test"]


@pytest.mark.parametrize("name", SETS)
def test_satirlar_kurallara_uygun(name: str) -> None:
    for row in rows(name):
        text, labels, tags = row["text"], row["labels"], row["tags"]
        assert isinstance(text, str)
        assert ALLOWED_CHARACTERS.fullmatch(text), text
        assert isinstance(labels, dict)
        assert isinstance(tags, list)
        assert set(labels) <= set(CHAT_CATEGORIES), text
        assert all(level in (1, 2, 3) for level in labels.values()), text
        assert set(tags) <= KNOWN_TAGS, text
        assert ("kapsam_disi" in tags) == (not labels), text
        assert ("coklu" in tags) == (len(labels) > 1), text
        assert ("tekil" in tags) == (len(labels) == 1), text


def test_test_seti_yeterli_ve_dengeli() -> None:
    data = rows("test")
    per_category = Counter(key for row in data for key in row["labels"])  # type: ignore[union-attr]

    assert len(data) >= 300
    assert all(per_category[c] >= 35 for c in CHAT_CATEGORIES), per_category
    assert sum(1 for row in data if not row["labels"]) >= 50
    assert sum(1 for row in data if len(row["labels"]) > 1) >= 25  # type: ignore[arg-type]


def test_setler_arasinda_ve_icinde_tekrar_yok() -> None:
    normalized = {name: [normalize(str(r["text"])) for r in rows(name)] for name in SETS}

    for name, texts in normalized.items():
        assert len(set(texts)) == len(texts), f"{name} içinde tekrar var"
    development = set(normalized["gelistirme"]) | set(normalized["gelistirme2"])
    assert not development & set(normalized["test"]), "test seti geliştirme setlerinden sızmış"


def test_test_seti_muhru_bozulmamis() -> None:
    """Test seti mühürlüdür (docs/siniflandirma.md); değiştirilirse yeni bir sürüm kaydı gerekir."""
    digest = hashlib.sha256((DATA / "test.jsonl").read_bytes()).hexdigest()

    assert digest == TEST_SET_SHA256
