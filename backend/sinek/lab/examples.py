"""Laboratuvar örnek deneyleri: makaledeki deneylerin gerçek simülasyonla üretilmiş raporları.

Raporlar `examples/` klasöründedir ve olduğu gibi gösterilir; kullanıcı aynı raporu yeniden
koşup sonucun birebir tuttuğunu doğrulayabilir.
"""

import re
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sinek.lab.report import ExperimentReport, load_report

EXAMPLES_DIR = Path(__file__).with_name("examples")
_NAME = re.compile(r"^[a-z0-9-]{1,60}$")


class ExampleInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    title_tr: str


class ExampleNotFoundError(LookupError):
    """İstenen örnek deney yok."""


@cache
def _load(name: str) -> ExperimentReport:
    return load_report((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def list_examples() -> list[ExampleInfo]:
    return [
        ExampleInfo(name=path.stem, title_tr=_load(path.stem).title_tr)
        for path in sorted(EXAMPLES_DIR.glob("*.json"))
    ]


def load_example(name: str) -> ExperimentReport:
    if not _NAME.fullmatch(name) or not (EXAMPLES_DIR / f"{name}.json").is_file():
        raise ExampleNotFoundError(name)
    return _load(name)
