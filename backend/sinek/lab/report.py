"""Deney raporu: dışa aktarma, geri yükleme ve yeniden koşarak doğrulama.

Rapor tek bir JSON dosyasıdır ve bir deneyi başka bir bilgisayarda tekrarlamak için gereken her
şeyi taşır: istek (uyarımlar, susturmalar, parametreler, tohum), çözümlenmiş nöron kimlikleri,
sonuçlar ve kaynak/kod sürümlerinin SHA-256 özetleri.

**Yeniden koşma.** Rapor geri yüklendiğinde aynı istek aynı tohumla tekrar çalıştırılır ve davranış
okumaları karşılaştırılır. Aynı donanımda sonuçlar birebir aynıdır. Farklı donanımda (ör. ekran
kartı ↔ işlemci) toplama sırası değişebileceğinden kayan nokta düzeyinde küçük farklar olabilir;
bu yüzden karşılaştırma hem birebir eşitliği hem de en büyük farkı raporlar.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch
from pydantic import BaseModel, ConfigDict, Field

from sinek import __version__
from sinek.connectome.connectome import Connectome
from sinek.connectome.download import sha256_of
from sinek.connectome.groups import Behavior, definitions_digest
from sinek.connectome.pipeline import IndexBundle, raw_dir
from sinek.connectome.sources import SOURCES
from sinek.decoder.decoder import CALIBRATION_PATH, BehaviorCalibration
from sinek.lab.experiment import (
    ExperimentRequest,
    ExperimentResult,
    ProgressLike,
    run_experiment,
)
from sinek.simulation.precompute import environment

REPORT_VERSION = 1
EXACT_TOLERANCE_HZ = 1e-9


class ReportError(ValueError):
    """Rapor okunamadı ya da bu sürümle uyumsuz."""


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sinek_version: str
    dataset: str = "FlyWire v783"
    sign_source: str = "reference"
    sources_sha256: dict[str, str]
    neuron_groups_definitions_sha256: str
    calibration_sha256: str
    environment: dict[str, str]


class ExperimentReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    report_version: int = REPORT_VERSION
    created_utc: str
    title_tr: str = Field(default="Laboratuvar deneyi", max_length=200)
    request: ExperimentRequest
    result: ExperimentResult
    provenance: Provenance


class BehaviorDifference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    behavior: Behavior
    condition: str
    reported_rate_hz: float
    replayed_rate_hz: float


class ReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identical: bool  # davranış okumaları birebir aynı mı
    max_difference_hz: float
    differences: list[BehaviorDifference]
    provenance_matches: bool  # veri ve tanım özetleri raporla aynı mı
    provenance_notes: list[str]
    result: ExperimentResult


def build_report(
    request: ExperimentRequest,
    result: ExperimentResult,
    data_dir: Path,
    title_tr: str | None = None,
) -> ExperimentReport:
    raw = raw_dir(data_dir)
    return ExperimentReport(
        created_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        title_tr=title_tr or "Laboratuvar deneyi",
        request=request,
        result=result,
        provenance=Provenance(
            sinek_version=__version__,
            sources_sha256={s.filename: s.sha256 for s in SOURCES if (raw / s.filename).is_file()},
            neuron_groups_definitions_sha256=definitions_digest(),
            calibration_sha256=sha256_of(CALIBRATION_PATH),
            environment=environment(),
        ),
    )


def save_report(path: Path, report: ExperimentReport) -> Path:
    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def load_report(data: str | bytes | dict[str, Any]) -> ExperimentReport:
    try:
        payload = json.loads(data) if isinstance(data, str | bytes) else data
        report = ExperimentReport.model_validate(payload)
    except (json.JSONDecodeError, ValueError) as error:
        raise ReportError(f"Rapor okunamadı: {error}") from error
    if report.report_version != REPORT_VERSION:
        raise ReportError(
            f"Rapor sürümü desteklenmiyor: {report.report_version} (beklenen {REPORT_VERSION})"
        )
    return report


def _behavior_rates(result: ExperimentResult) -> dict[tuple[Behavior, str], float]:
    rates = {(b.behavior, "kontrol"): b.rate_hz for b in result.control.output.behaviors}
    if result.silenced_condition is not None:
        rates.update(
            {
                (b.behavior, "susturma"): b.rate_hz
                for b in result.silenced_condition.output.behaviors
            }
        )
    return rates


def _provenance_notes(report: ExperimentReport, data_dir: Path) -> list[str]:
    notes = []
    raw = raw_dir(data_dir)
    current_sources = {s.filename: s.sha256 for s in SOURCES if (raw / s.filename).is_file()}
    for filename, digest in report.provenance.sources_sha256.items():
        if current_sources.get(filename) != digest:
            notes.append(f"Kaynak dosya farklı: {filename}")
    if report.provenance.neuron_groups_definitions_sha256 != definitions_digest():
        notes.append("Nöron grubu tanımları rapordan farklı")
    if report.provenance.calibration_sha256 != sha256_of(CALIBRATION_PATH):
        notes.append("Kalibrasyon dosyası rapordan farklı")
    return notes


def replay_report(
    report: ExperimentReport,
    bundle: IndexBundle,
    connectome: Connectome,
    calibration: dict[Behavior, BehaviorCalibration],
    data_dir: Path,
    device: torch.device | None = None,
    reporter: ProgressLike | None = None,
) -> ReplayResult:
    """Raporu yeniden koşar ve davranış okumalarını rapordakilerle karşılaştırır."""
    notes = _provenance_notes(report, data_dir)
    result = run_experiment(
        report.request, bundle, connectome, calibration, device=device, reporter=reporter
    )

    reported, replayed = _behavior_rates(report.result), _behavior_rates(result)
    differences = [
        BehaviorDifference(
            behavior=behavior,
            condition=condition,
            reported_rate_hz=rate,
            replayed_rate_hz=replayed.get((behavior, condition), float("nan")),
        )
        for (behavior, condition), rate in reported.items()
        if abs(rate - replayed.get((behavior, condition), float("nan"))) > EXACT_TOLERANCE_HZ
    ]
    largest = max(
        (abs(d.reported_rate_hz - d.replayed_rate_hz) for d in differences),
        default=0.0,
    )
    return ReplayResult(
        identical=not differences,
        max_difference_hz=largest,
        differences=differences,
        provenance_matches=not notes,
        provenance_notes=notes,
        result=result,
    )
