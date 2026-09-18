"""Sınıflandırıcı değerlendirmesi: kategori bazında kesinlik, duyarlılık, F1 ve alt kırılımlar."""

import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sinek.stimulus.lexicon import CATEGORIES

DATA_DIR = Path(__file__).with_name("data")
OUT_OF_SCOPE = "kapsam_disi"
Predictor = Callable[[str], dict[str, int]]


@dataclass(frozen=True)
class Example:
    text: str
    labels: dict[str, int]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ClassScore:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True)
class Evaluation:
    macro_f1: float
    per_class: dict[str, ClassScore]
    exact_match: float
    intensity_accuracy: float  # doğru bulunan kategorilerde düzey doğruluğu
    per_tag_exact: dict[str, float]
    errors: tuple[tuple[str, dict[str, int], dict[str, int]], ...]


def load_examples(name: str) -> list[Example]:
    lines = (DATA_DIR / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    return [
        Example(row["text"], row["labels"], tuple(row["tags"]))
        for row in (json.loads(line) for line in lines if line.strip())
    ]


def _classes(labels: dict[str, int]) -> set[str]:
    return set(labels) if labels else {OUT_OF_SCOPE}


def evaluate(predict: Predictor, examples: list[Example]) -> Evaluation:
    counts = {c: [0, 0, 0] for c in (*CATEGORIES, OUT_OF_SCOPE)}  # tp, fp, fn
    exact = 0
    level_hits = level_total = 0
    tag_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    errors = []

    for example in examples:
        predicted = predict(example.text)
        truth, guess = _classes(example.labels), _classes(predicted)
        for c in counts:
            counts[c][0] += c in truth and c in guess
            counts[c][1] += c not in truth and c in guess
            counts[c][2] += c in truth and c not in guess
        correct = truth == guess
        exact += correct
        for c in set(example.labels) & set(predicted):
            level_total += 1
            level_hits += example.labels[c] == predicted[c]
        for tag in example.tags:
            tag_totals[tag][0] += correct
            tag_totals[tag][1] += 1
        if not correct:
            errors.append((example.text, example.labels, predicted))

    per_class = {}
    for c, (tp, fp, fn) in counts.items():
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[c] = ClassScore(precision, recall, f1, tp + fn)

    return Evaluation(
        macro_f1=sum(s.f1 for s in per_class.values()) / len(per_class),
        per_class=per_class,
        exact_match=exact / len(examples),
        intensity_accuracy=level_hits / level_total if level_total else 0.0,
        per_tag_exact={tag: hit / total for tag, (hit, total) in sorted(tag_totals.items())},
        errors=tuple(errors),
    )


def format_evaluation(result: Evaluation, show_errors: bool = True) -> str:
    lines = [
        f"Makro F1: {result.macro_f1:.3f} | tam eşleşme: %{100 * result.exact_match:.1f} | "
        f"yoğunluk doğruluğu: %{100 * result.intensity_accuracy:.1f}",
        "",
        f"{'sınıf':16} {'kesinlik':>9} {'duyarlılık':>11} {'F1':>6} {'destek':>7}",
    ]
    for name, s in result.per_class.items():
        lines.append(f"{name:16} {s.precision:9.2f} {s.recall:11.2f} {s.f1:6.2f} {s.support:7d}")
    lines += ["", "Etiket alt kırılımı (tam eşleşme):"]
    lines += [f"  {tag:14} %{100 * v:.0f}" for tag, v in result.per_tag_exact.items()]
    if show_errors:
        lines += ["", f"Hatalar ({len(result.errors)}):"]
        lines += [
            f"  {text!r}: beklenen {truth}, tahmin {guess}" for text, truth, guess in result.errors
        ]
    return "\n".join(lines)
