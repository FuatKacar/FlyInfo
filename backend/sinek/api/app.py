"""FastAPI uygulama fabrikası.

Uç noktalar:
    GET  /api/health               sürüm, LLM ve veri durumu
    POST /api/chat                 Türkçe mesaj → tüm katmanların ara çıktılarıyla yanıt
    POST /api/stimulate            doğrudan uyarım (metin ve LLM katmanı yok)
    GET  /api/scenarios            uyarım grupları, senaryo seti ve hazır paket durumu
    GET  /api/neurons/{cell_type}  bir hücre tipinin FlyWire nöronları
    GET  /api/neurons/search       hücre tipi arama (Laboratuvar seçici)
    GET  /api/lab/options          seçilebilir gruplar, nöropiller, sınırlar
    GET  /api/lab/examples         makaledeki deneylerin hazır raporları (liste / tek rapor)
    POST /api/lab/run              doğrudan uyarım + susturma deneyi (arka plan işi başlatır)
    GET  /api/lab/jobs/{job_id}    iş durumu, ilerleme ve sonuç
    POST /api/lab/pathways         uyarımdan davranış nöronuna en güçlü sinyal yolları
    POST /api/lab/report           deneyi koşar ve tekrarlanabilir rapor döndürür
    POST /api/lab/replay           raporu yeniden koşar ve sonuçları karşılaştırır
"""

import threading
from collections.abc import Callable, Hashable
from pathlib import Path as FilePath
from typing import Annotated, Any, Literal

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from sinek import __version__
from sinek.chat.service import BrainService, ChatService, Services, build_services
from sinek.config import LLMProvider, get_settings
from sinek.connectome.groups import Behavior
from sinek.decoder.schema import DecoderOutput
from sinek.lab.examples import ExampleInfo, ExampleNotFoundError, list_examples, load_example
from sinek.lab.experiment import (
    MAX_RATE_HZ,
    MAX_SILENCED,
    MAX_STIMULI,
    ExperimentRequest,
    ExperimentResult,
)
from sinek.lab.jobs import Job, JobRegistry, JobState, ProgressReporter
from sinek.lab.pathways import MAX_HOPS, Pathway
from sinek.lab.report import ExperimentReport, ReplayResult, ReportError, load_report
from sinek.lab.selection import TRANSMITTERS, SelectionError, search_cell_types
from sinek.lab.service import LabService
from sinek.presentation.locale import texts
from sinek.simulation.scenarios import F_MAX_HZ, make_scenario, scenario_set

# Sinyal yollarının yanında her zaman gösterilen sınırlılık notu (yol haritası 3.5, L3).
PATHWAY_NOTE_TR = (
    "Yollar yapısal ve korelasyonel bir özettir, nedensellik kanıtı değildir. Bir yolun "
    "gerekliliğini sınamak için o yoldaki nöronları susturun."
)

# Derlenmiş arayüz (frontend: npm run build). Yoksa yalnızca API sunulur.
WEB_DIR = FilePath(__file__).resolve().parent.parent / "web"

# Parlaklık ölçeğinin alt referansı: bu hızın altı sönük kalır (docs/yol-haritasi.md 3.5).
BRIGHTNESS_REFERENCE_HZ = 0.5


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(_Model):
    status: Literal["ok"]
    version: str
    llm_provider: LLMProvider
    llm_enabled: bool


class ChatRequest(_Model):
    message: str = Field(min_length=1, max_length=1000)


class EvidenceItem(_Model):
    category: str
    term: str
    clause: str
    rule: str


class ClassificationInfo(_Model):
    in_scope: bool
    levels: dict[str, int]  # kategori → yoğunluk düzeyi (1–3)
    evidence: list[EvidenceItem]
    out_of_scope_reason: str | None


class PresentationInfo(_Model):
    text: str
    source: Literal["llm", "template"]
    provider: str | None
    model: str | None
    fallback_reason: str | None


class OutOfScopeHint(_Model):
    title: str
    examples: list[str]


class BrainScale(_Model):
    """Beyin şeması parlaklık ölçeği (tüm senaryolarda sabit):

    parlaklık = log10(1 + hız / reference_hz) / log10(1 + max_hz / reference_hz), [0, 1]'e kırpılır.
    """

    reference_hz: float = BRIGHTNESS_REFERENCE_HZ
    max_hz: float = F_MAX_HZ


class BrainActivity(_Model):
    # nöropil → sinaps ağırlıklı ortalama ateşleme hızı (Hz); 30 deneme ortalaması
    neuropil_rates_hz: dict[str, float]
    scale: BrainScale = BrainScale()


class ChatResponse(_Model):
    classification: ClassificationInfo
    output: DecoderOutput
    brain: BrainActivity
    presentation: PresentationInfo
    hint: OutOfScopeHint | None  # yalnızca kapsam dışı mesajlarda; simülasyonun parçası değildir


class StimulusRequestItem(_Model):
    group: str
    intensity: float = Field(gt=0, le=1)


class StimulateRequest(_Model):
    components: list[StimulusRequestItem] = Field(max_length=8)


class StimulateResponse(_Model):
    output: DecoderOutput
    brain: BrainActivity


class StimulusGroupInfo(_Model):
    key: str
    name_tr: str
    description_tr: str
    neuron_count: int
    circuit_only: bool
    citations: list[int]


class ScenarioInfo(_Model):
    key: str
    components: list[tuple[str, float]]
    precomputed: bool


class PackageInfo(_Model):
    available: bool
    version: str | None
    problem: str | None


class ScenariosResponse(_Model):
    groups: list[StimulusGroupInfo]
    package: PackageInfo
    scenarios: list[ScenarioInfo]


class NeuronInfo(_Model):
    root_id: str  # 64 bit kimlik; JavaScript sayı hassasiyeti için metin
    in_model: bool
    side: str | None
    super_class: str | None
    cell_class: str | None
    top_nt: str | None
    top_nt_conf: float | None
    groups: list[str]


class CellTypeResponse(_Model):
    cell_type: str
    neuron_count: int
    in_model_count: int
    neurons: list[NeuronInfo]


class PathwayRequest(_Model):
    experiment: ExperimentRequest
    behavior: Behavior
    top_k: int = Field(default=5, ge=1, le=20)
    max_hops: int = Field(default=MAX_HOPS, ge=1, le=6)


class PathwayResponse(_Model):
    target_id: str  # yolların ulaştığı okuma nöronu (FlyWire kimliği)
    pathways: list[Pathway]
    note_tr: str


class ReportRequest(_Model):
    experiment: ExperimentRequest
    title_tr: str | None = Field(default=None, max_length=200)


class LabGroupInfo(_Model):
    key: str
    name_tr: str
    role: str
    neuron_count: int
    behavior: Behavior | None


class LabOptions(_Model):
    groups: list[LabGroupInfo]
    neuropils: list[str]
    neurotransmitters: list[str]
    limits: dict[str, float]
    busy: bool


class CellTypeMatch(_Model):
    cell_type: str
    neuron_count: int


class JobStatus(_Model):
    """Arka planda çalışan Laboratuvar işi. Sonuç, işin türüne göre ilgili alanda döner."""

    id: str
    kind: Literal["run", "pathways", "report", "replay"]
    state: JobState
    progress: float = Field(ge=0, le=1)
    step_tr: str
    error_tr: str | None = None
    experiment: ExperimentResult | None = None
    pathways: PathwayResponse | None = None
    report: ExperimentReport | None = None
    replay: ReplayResult | None = None


def _job_status(job: Job) -> JobStatus:
    payload: dict[str, Any] = {
        "id": job.id,
        "kind": job.kind,
        "state": job.state,
        "progress": round(job.progress, 4),
        "step_tr": job.step_tr,
        "error_tr": job.error_tr,
    }
    if job.state is JobState.DONE:
        payload[{"run": "experiment"}.get(job.kind, job.kind)] = job.result
    return JobStatus.model_validate(payload)


class _ServiceHolder:
    """Veri yüklemesi ağır olduğundan servisler ilk ihtiyaçta bir kez kurulur."""

    def __init__(self, factory: Callable[[], Services]) -> None:
        self._factory = factory
        self._lock = threading.Lock()
        self._built: Services | None = None

    def get(self) -> Services:
        with self._lock:
            if self._built is None:
                try:
                    self._built = self._factory()
                except FileNotFoundError as error:
                    raise HTTPException(
                        503,
                        f"FlyWire verisi bulunamadı ({error.filename}). Önce: uv run sinek indir",
                    ) from error
            return self._built


def create_app(
    factory: Callable[[], Services] | None = None,
    web_dir: FilePath = WEB_DIR,
) -> FastAPI:
    app = FastAPI(
        title="FlyInfo",
        version=__version__,
        description="Drosophila konektomu üzerinde şeffaf beyin simülasyonu API'si",
        # Tek şema: istek ve yanıt aynı tipleri kullanır (ör. FlyWire kimlikleri her yönde metin).
        separate_input_output_schemas=False,
    )
    services = _ServiceHolder(factory or (lambda: build_services(get_settings())))
    jobs = JobRegistry()

    def brain() -> BrainService:
        return services.get().brain

    def chat() -> ChatService:
        return services.get().chat

    def lab() -> LabService:
        return services.get().lab

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        settings = get_settings()
        return HealthResponse(
            status="ok",
            version=__version__,
            llm_provider=settings.llm_provider,
            llm_enabled=settings.llm_enabled,
        )

    @app.post("/api/chat", response_model=ChatResponse)
    def post_chat(
        request: ChatRequest, service: Annotated[ChatService, Depends(chat)]
    ) -> ChatResponse:
        reply = service.reply(request.message)
        c, p = reply.classification, reply.presentation
        hint_texts = texts()["chat"]
        return ChatResponse(
            classification=ClassificationInfo(
                in_scope=c.in_scope,
                levels=c.levels,
                evidence=[EvidenceItem(**vars(e)) for e in c.evidence],
                out_of_scope_reason=c.out_of_scope_reason,
            ),
            output=reply.output,
            brain=BrainActivity(neuropil_rates_hz=reply.simulation.neuropil_rates_hz),
            presentation=PresentationInfo(
                text=p.text,
                source=p.source,
                provider=p.provider,
                model=p.model,
                fallback_reason=p.fallback_reason,
            ),
            hint=None
            if c.in_scope
            else OutOfScopeHint(
                title=hint_texts["out_of_scope_hint_title"],
                examples=list(hint_texts["out_of_scope_examples"]),
            ),
        )

    @app.post("/api/stimulate", response_model=StimulateResponse)
    def post_stimulate(
        request: StimulateRequest, service: Annotated[BrainService, Depends(brain)]
    ) -> StimulateResponse:
        try:
            scenario = make_scenario(*((c.group, c.intensity) for c in request.components))
            unknown = [g for g, _ in scenario.components if g not in service.stimulus_groups]
            if unknown:
                raise ValueError(f"Bilinmeyen uyarım grubu: {', '.join(unknown)}")
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        view = service.run(scenario)
        return StimulateResponse(
            output=view.output, brain=BrainActivity(neuropil_rates_hz=view.neuropil_rates_hz)
        )

    @app.get("/api/scenarios", response_model=ScenariosResponse)
    def get_scenarios(
        service: Annotated[BrainService, Depends(brain)],
    ) -> ScenariosResponse:
        package = service.store.package
        problem = services.get().package_problem
        return ScenariosResponse(
            groups=[
                StimulusGroupInfo(
                    key=key,
                    name_tr=group.definition.name_tr,
                    description_tr=group.definition.description_tr,
                    neuron_count=group.size,
                    circuit_only=group.definition.circuit_only,
                    citations=list(group.definition.citations),
                )
                for key in service.stimulus_groups
                for group in [service.index.groups[key]]
            ],
            package=PackageInfo(
                available=package is not None,
                version=package.version if package else None,
                problem=problem,
            ),
            scenarios=[
                ScenarioInfo(
                    key=s.key,
                    components=list(s.components),
                    precomputed=package is not None and s in package,
                )
                for s in scenario_set()
            ],
        )

    def _lab_error(error: Exception) -> HTTPException:
        return HTTPException(422, str(error))

    @app.get("/api/lab/options", response_model=LabOptions)
    def get_lab_options(service: Annotated[LabService, Depends(lab)]) -> LabOptions:
        groups = [
            LabGroupInfo(
                key=key,
                name_tr=group.definition.name_tr,
                role=group.definition.role.value,
                neuron_count=group.size,
                behavior=group.definition.behavior,
            )
            for key, group in service.index.groups.items()
        ]
        neuropils = list(service.index.neuropils.names) if service.index.neuropils else []
        return LabOptions(
            groups=groups,
            neuropils=neuropils,
            neurotransmitters=list(TRANSMITTERS),
            limits={
                "max_rate_hz": MAX_RATE_HZ,
                "max_stimuli": MAX_STIMULI,
                "max_silenced": MAX_SILENCED,
                "max_trials": 50,
                "max_run_ms": 2000,
            },
            busy=service.busy,
        )

    @app.get("/api/lab/examples", response_model=list[ExampleInfo])
    def get_lab_examples() -> list[ExampleInfo]:
        return list_examples()

    @app.get("/api/lab/examples/{name}", response_model=ExperimentReport)
    def get_lab_example(name: str) -> ExperimentReport:
        try:
            return load_example(name)
        except ExampleNotFoundError as error:
            raise HTTPException(404, f"Örnek deney bulunamadı: {name}") from error

    @app.get("/api/neurons/search", response_model=list[CellTypeMatch])
    def get_neuron_search(
        service: Annotated[LabService, Depends(lab)],
        q: Annotated[str, Query(min_length=1, max_length=100)],
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> list[CellTypeMatch]:
        try:
            matches = search_cell_types(service.index, q, limit)
        except SelectionError as error:
            raise _lab_error(error) from error
        return [CellTypeMatch.model_validate(match) for match in matches]

    def _start(
        kind: str, service: LabService, work: Callable[[ProgressReporter], Any]
    ) -> JobStatus:
        if service.busy:
            raise HTTPException(409, "Başka bir deney çalışıyor; bitmesini bekleyin")
        return _job_status(jobs.start(kind, work))

    @app.post("/api/lab/run", response_model=JobStatus, status_code=202)
    def post_lab_run(
        request: ExperimentRequest, service: Annotated[LabService, Depends(lab)]
    ) -> JobStatus:
        return _start("run", service, lambda reporter: service.run(request, reporter))

    @app.get("/api/lab/jobs/{job_id}", response_model=JobStatus)
    def get_lab_job(job_id: str) -> JobStatus:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(404, f"İş bulunamadı: {job_id}")
        return _job_status(job)

    @app.post("/api/lab/pathways", response_model=JobStatus, status_code=202)
    def post_lab_pathways(
        request: PathwayRequest, service: Annotated[LabService, Depends(lab)]
    ) -> JobStatus:
        def work(_reporter: ProgressReporter) -> PathwayResponse:
            paths, target = service.pathways(
                request.experiment, request.behavior, request.top_k, request.max_hops
            )
            return PathwayResponse(target_id=target, pathways=paths, note_tr=PATHWAY_NOTE_TR)

        return _start("pathways", service, work)

    @app.post("/api/lab/report", response_model=JobStatus, status_code=202)
    def post_lab_report(
        request: ReportRequest, service: Annotated[LabService, Depends(lab)]
    ) -> JobStatus:
        return _start(
            "report",
            service,
            lambda reporter: service.report(request.experiment, request.title_tr, reporter),
        )

    @app.post("/api/lab/replay", response_model=JobStatus, status_code=202)
    def post_lab_replay(
        report: dict[str, Any], service: Annotated[LabService, Depends(lab)]
    ) -> JobStatus:
        try:
            loaded = load_report(report)  # biçim hatası hemen bildirilir, işe girmeden
        except ReportError as error:
            raise _lab_error(error) from error
        return _start("replay", service, lambda reporter: service.replay(loaded, reporter))

    @app.get("/api/neurons/{cell_type}", response_model=CellTypeResponse)
    def get_neurons(
        cell_type: Annotated[str, Path(min_length=1, max_length=100)],
        service: Annotated[BrainService, Depends(brain)],
    ) -> CellTypeResponse:
        annotations = service.index.annotations
        rows = annotations[annotations["cell_type"] == cell_type]
        if rows.empty:
            raise HTTPException(404, f"Hücre tipi bulunamadı: {cell_type}")
        ids = rows.index.to_numpy(dtype=np.int64)
        _, missing = service.index.neurons.index_of(ids)
        missing_set = set(missing)
        membership: dict[int, list[str]] = {}
        for key, group in service.index.groups.items():
            for root_id in group.flywire_ids:
                membership.setdefault(root_id, []).append(key)
        records: list[dict[Hashable, Any]] = (
            rows.astype(object).where(rows.notna(), None).to_dict("records")
        )
        neurons = []
        for root_id, row in zip(ids.tolist(), records, strict=True):
            conf = row["top_nt_conf"]
            neurons.append(
                NeuronInfo(
                    root_id=str(root_id),
                    in_model=root_id not in missing_set,
                    side=row["side"],
                    super_class=row["super_class"],
                    cell_class=row["cell_class"],
                    top_nt=row["top_nt"],
                    top_nt_conf=None if conf is None else float(conf),
                    groups=membership.get(root_id, []),
                )
            )
        return CellTypeResponse(
            cell_type=cell_type,
            neuron_count=len(neurons),
            in_model_count=sum(n.in_model for n in neurons),
            neurons=neurons,
        )

    if (web_dir / "index.html").is_file():
        # API yollarından sonra bağlanır; /api/* her zaman önceliklidir.
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="arayuz")

    return app
