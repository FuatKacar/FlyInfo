"""Laboratuvar servisi: tam konektomu bir kez yükler, deneyleri sıraya koyar, sonucu önbelleğe alır.

Aynı anda tek deney çalışır (ekran kartı belleği ve ölçüm tekrarlanabilirliği için). Bir deneyin
nöron hızları yerel önbelleğe yazılır; böylece aynı deney için sinyal yolu sorgusu simülasyonu
yeniden koşmaz.
"""

import hashlib
import threading
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray

from sinek.connectome.groups import Behavior, GroupRole, definitions_digest
from sinek.connectome.pipeline import DataBundle, IndexBundle, load_bundle
from sinek.connectome.sources import SOURCES
from sinek.decoder.decoder import BehaviorCalibration, load_calibration
from sinek.lab.experiment import (
    ExperimentRequest,
    ExperimentResult,
    ProgressLike,
    run_experiment,
)
from sinek.lab.pathways import MAX_HOPS, Pathway, PathwayError, strongest_paths
from sinek.lab.report import ExperimentReport, ReplayResult, build_report, replay_report
from sinek.lab.selection import indices_of, resolve_selector
from sinek.simulation.lif import Stimulus, simulate


class LabService:
    def __init__(
        self,
        index: IndexBundle,
        data_dir: Path,
        cache_dir: Path,
        calibration: dict[Behavior, BehaviorCalibration] | None = None,
        device: torch.device | None = None,
    ) -> None:
        self.index = index
        self._data_dir = data_dir
        self._cache_dir = cache_dir / "lab"
        self._calibration = calibration or load_calibration()
        self._device = device
        self._bundle: DataBundle | None = None
        self._lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def _full_bundle(self) -> DataBundle:
        if self._bundle is None:
            self._bundle = load_bundle(self._data_dir)
        return self._bundle

    def run(
        self, request: ExperimentRequest, reporter: ProgressLike | None = None
    ) -> ExperimentResult:
        with self._lock:
            bundle = self._full_bundle()
            return run_experiment(
                request,
                self.index,
                bundle.connectome,
                self._calibration,
                device=self._device,
                reporter=reporter,
            )

    def report(
        self,
        request: ExperimentRequest,
        title_tr: str | None = None,
        reporter: ProgressLike | None = None,
    ) -> ExperimentReport:
        result = self.run(request, reporter)
        return build_report(request, result, self._data_dir, title_tr)

    def replay(
        self, report: ExperimentReport, reporter: ProgressLike | None = None
    ) -> ReplayResult:
        with self._lock:
            bundle = self._full_bundle()
            return replay_report(
                report,
                self.index,
                bundle.connectome,
                self._calibration,
                self._data_dir,
                device=self._device,
                reporter=reporter,
            )

    def pathways(
        self,
        request: ExperimentRequest,
        behavior: Behavior,
        top_k: int = 5,
        max_hops: int = MAX_HOPS,
    ) -> tuple[list[Pathway], str]:
        """Uyarılan nöronlardan davranışın en hızlı okuma nöronuna giden en güçlü yollar."""
        rates = self._rates(request)
        readouts = [
            group
            for group in self.index.groups.values()
            if group.definition.role is GroupRole.READOUT and group.definition.behavior is behavior
        ]
        candidates = np.concatenate([g.indices for g in readouts]) if readouts else np.empty(0, int)
        if candidates.size == 0:
            raise PathwayError(f"Bu davranışın okuma nöronu tanımlı değil: {behavior.value}")
        target = int(candidates[int(np.argmax(rates[candidates]))])
        sources = np.unique(
            np.concatenate(
                [
                    indices_of(resolve_selector(s.selector, self.index), self.index)
                    for s in request.stimuli
                ]
            )
        )
        bundle = self._full_bundle()
        paths = strongest_paths(
            bundle.connectome, rates, sources, target, top_k=top_k, max_hops=max_hops
        )
        return [self._with_cell_types(path) for path in paths], str(
            self.index.neurons.flywire_ids[target]
        )

    def _with_cell_types(self, path: Pathway) -> Pathway:
        """Yol düğümlerine hücre tipi adlarını ekler (18 haneli kimlikler okunmaz)."""
        types = self.index.annotations["cell_type"]

        def cell_type(root_id: str) -> str | None:
            value = types.get(int(root_id))
            return None if value is None or value != value else str(value)  # NaN → None

        edges = [
            edge.model_copy(
                update={
                    "pre_cell_type": cell_type(edge.pre_id),
                    "post_cell_type": cell_type(edge.post_id),
                }
            )
            for edge in path.edges
        ]
        return path.model_copy(update={"edges": edges})

    def _cache_key(self, request: ExperimentRequest) -> str:
        payload = {
            "request": request.model_dump(mode="json"),
            "definitions": definitions_digest(),
            "sources": {s.filename: s.sha256 for s in SOURCES},
        }
        return hashlib.sha256(repr(sorted(payload.items())).encode()).hexdigest()[:32]

    def _rates(self, request: ExperimentRequest) -> NDArray[np.float64]:
        """Uyarımın (susturmasız) nöron hızları; aynı istek için yerel önbellekten okunur."""
        path = self._cache_dir / f"{self._cache_key(request)}.npy"
        if path.is_file():
            cached: NDArray[np.float64] = np.load(path)
            if cached.shape == (self.index.neurons.n_neurons,):
                return cached
        with self._lock:
            bundle = self._full_bundle()
            stimuli = [
                Stimulus(
                    indices_of(resolve_selector(s.selector, self.index), self.index), s.rate_hz
                )
                for s in request.stimuli
            ]
            result = simulate(
                bundle.connectome,
                stimuli,
                params=request.params.to_lif(),
                seed=request.params.seed,
                device=self._device,
            )
        rates = result.rates_hz
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(path, rates)
        return rates
