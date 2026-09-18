"""Uzun süren Laboratuvar işleri: arka planda çalıştırma ve ilerleme bildirimi.

Bir deney tam beyinde ~1,5 dakika sürer. Arayüzün donmaması ve kullanıcının ilerlemeyi görmesi için
işler arka planda çalışır; istemci iş durumunu sorgular (kısa aralıklı yoklama). Aynı anda tek iş
çalışır: `LabService` zaten kilitlidir, kuyruk bunu görünür kılar.

İş durumları: `queued` → `running` → `done` | `error` | `cancelled`.
"""

import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

MAX_JOBS = 20  # bellekte tutulan en son iş sayısı


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    kind: str
    created_utc: str
    state: JobState = JobState.QUEUED
    progress: float = 0.0  # 0–1
    step_tr: str = "sırada"
    result: Any = None
    error_tr: str | None = None

    def snapshot(self) -> "Job":
        return Job(**{**self.__dict__})


@dataclass
class _Registry:
    jobs: OrderedDict[str, Job] = field(default_factory=OrderedDict)
    lock: threading.Lock = field(default_factory=threading.Lock)


class JobRegistry:
    """İşleri başlatır, ilerlemelerini saklar ve en son `MAX_JOBS` işi bellekte tutar."""

    def __init__(self, max_jobs: int = MAX_JOBS) -> None:
        self._state = _Registry()
        self._max_jobs = max_jobs

    def start(self, kind: str, work: Callable[["ProgressReporter"], Any]) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:16],
            kind=kind,
            created_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        with self._state.lock:
            self._state.jobs[job.id] = job
            while len(self._state.jobs) > self._max_jobs:
                self._state.jobs.popitem(last=False)

        def run() -> None:
            reporter = ProgressReporter(self, job.id)
            self._update(job.id, state=JobState.RUNNING, step_tr="çalışıyor")
            try:
                result = work(reporter)
            except Exception as error:  # kullanıcıya anlaşılır mesaj, sunucu ayakta kalır
                self._update(job.id, state=JobState.ERROR, error_tr=str(error), progress=1.0)
            else:
                self._update(
                    job.id,
                    state=JobState.DONE,
                    result=result,
                    progress=1.0,
                    step_tr="tamamlandı",
                )

        threading.Thread(target=run, name=f"lab-{kind}-{job.id}", daemon=True).start()
        return job.snapshot()

    def get(self, job_id: str) -> Job | None:
        with self._state.lock:
            job = self._state.jobs.get(job_id)
            return job.snapshot() if job else None

    def _update(self, job_id: str, **changes: Any) -> None:
        with self._state.lock:
            job = self._state.jobs.get(job_id)
            if job is None:  # pragma: no cover - iş listeden düşmüş olabilir
                return
            for key, value in changes.items():
                setattr(job, key, value)


@dataclass
class ProgressReporter:
    """İşin içinden ilerleme bildirir; `simulate` geri çağrısına bağlanır."""

    registry: JobRegistry
    job_id: str
    _offset: float = 0.0
    _span: float = 1.0

    def stage(self, step_tr: str, offset: float, span: float) -> None:
        """Bu aşamanın toplam ilerleme içindeki payını belirler (ör. kontrol koşulu 0–0,5)."""
        self._offset, self._span = offset, span
        self.registry._update(self.job_id, step_tr=step_tr, progress=offset)

    def __call__(self, step: int, total: int) -> None:
        fraction = step / total if total else 1.0
        self.registry._update(self.job_id, progress=self._offset + self._span * fraction)
