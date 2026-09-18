"""Senaryo sonuçlarının kaynağı: doğrulanmış hazır paket, yoksa canlı simülasyon.

Hazır paket yalnızca manifesti mevcut koşullarla uyuşuyorsa kullanılır:
    - şema ve paket sürümü beklenen değerde,
    - nöron grubu TANIMLARI (neuron_groups.toml içeriği) değişmemiş; dosyadaki yorum ve biçim
      değişiklikleri paketi geçersiz kılmaz,
    - manifestteki kaynak dosya özetleri koddaki sabit özetlerle aynı,
    - okunan her senaryo dosyasının SHA-256 özeti manifestteki değerle aynı.

Canlı simülasyon hazır paketle aynı kodu (`run_scenario`) ve aynı tohum kuralını kullanır; sonuç
yerel önbelleğe yazılır. Önbellek dosyasının adı sonucu belirleyen girdilerin özetini içerir, bu
yüzden girdiler değişince eski sonuç kullanılmaz.
"""

import hashlib
import json
import threading
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from sinek.connectome.download import sha256_of
from sinek.connectome.groups import DEFAULT_GROUPS_PATH, GroupDefinition, definitions_digest
from sinek.connectome.pipeline import DataBundle, load_bundle
from sinek.connectome.sources import SOURCES
from sinek.simulation.params import LIFParams
from sinek.simulation.precompute import (
    PACKAGE_VERSION,
    SCHEMA_VERSION,
    ScenarioResult,
    load_result,
    run_scenario,
    save_result,
    scenario_seed,
)
from sinek.simulation.scenarios import F_MAX_HZ, Scenario


class PackageError(RuntimeError):
    """Hazır senaryo paketi eksik, bozuk veya mevcut koşullarla uyumsuz."""


class ResultSource(StrEnum):
    PRECOMPUTED = "precomputed"
    LIVE = "live"


@dataclass(frozen=True)
class StoredResult:
    result: ScenarioResult
    source: ResultSource
    seed: int
    package_version: str | None


class ScenarioPackage:
    def __init__(self, directory: Path, manifest: dict[str, Any]) -> None:
        self.directory = directory
        self._manifest = manifest

    @classmethod
    def open(
        cls,
        directory: Path,
        params: LIFParams | None = None,
        definitions: dict[str, GroupDefinition] | None = None,
        groups_path: Path = DEFAULT_GROUPS_PATH,
    ) -> "ScenarioPackage":
        path = directory / "manifest.json"
        if not path.is_file():
            raise PackageError(f"Manifest yok: {path} (paket eksik ya da hesaplama sürüyor)")
        manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise PackageError(f"Desteklenmeyen şema sürümü: {manifest.get('schema_version')}")
        if manifest.get("package_version") != PACKAGE_VERSION:
            raise PackageError(f"Beklenmeyen paket sürümü: {manifest.get('package_version')}")
        expected_groups = manifest.get("neuron_groups_definitions_sha256")
        if expected_groups is None:  # eski paketler yalnızca dosya özeti taşır
            expected_groups, actual_groups = (
                manifest.get("neuron_groups_sha256"),
                sha256_of(groups_path),
            )
        else:
            actual_groups = definitions_digest(definitions)
        if expected_groups != actual_groups:
            raise PackageError("Nöron grubu tanımları paket üretildikten sonra değişmiş")
        expected = {s.filename: s.sha256 for s in SOURCES}
        for filename, digest in manifest.get("sources", {}).items():
            if expected.get(filename) != digest:
                raise PackageError(f"Paket farklı bir kaynak dosyayla üretilmiş: {filename}")
        if (
            manifest.get("f_max_hz") != F_MAX_HZ
            or manifest.get("params") != (params or LIFParams()).to_dict()
        ):
            raise PackageError("Paket farklı model parametreleriyle üretilmiş")
        return cls(directory, manifest)

    @property
    def version(self) -> str:
        return str(self._manifest["package_version"])

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(self._manifest["scenarios"])

    def __contains__(self, scenario: Scenario) -> bool:
        return scenario.key in self._manifest["scenarios"]

    def load(self, scenario: Scenario) -> ScenarioResult:
        entry = self._manifest["scenarios"].get(scenario.key)
        if entry is None:
            raise KeyError(scenario.key)
        path = self.directory / entry["file"]
        if not path.is_file() or sha256_of(path) != entry["sha256"]:
            raise PackageError(f"Senaryo dosyası eksik veya bozuk: {path.name}")
        return load_result(path, scenario)


def live_cache_name(
    scenario: Scenario, params: LIFParams, definitions: dict[str, GroupDefinition] | None = None
) -> str:
    """Canlı sonucun önbellek adı: senaryo anahtarı + sonucu belirleyen girdilerin özeti."""
    payload = {
        "package_version": PACKAGE_VERSION,
        "scenario": scenario.key,
        "seed": scenario_seed(scenario.key),
        "params": params.to_dict(),
        "f_max_hz": F_MAX_HZ,
        "sign_source": "reference",
        "sources": {s.filename: s.sha256 for s in SOURCES},
        "neuron_groups_definitions_sha256": definitions_digest(definitions),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"{scenario.key}-{digest[:16]}.npz"


class LiveSimulator:
    """Hazır pakette bulunmayan senaryoları kullanıcının bilgisayarında simüle eder.

    Tam konektom ilk ihtiyaçta bir kez yüklenir. Aynı anda tek simülasyon çalışır (GPU belleği).
    """

    def __init__(
        self,
        data_dir: Path,
        cache_dir: Path,
        params: LIFParams | None = None,
    ) -> None:
        self._data_dir = data_dir
        self._cache_dir = cache_dir / "scenarios"
        self._params = params or LIFParams()
        self._bundle: DataBundle | None = None
        self._lock = threading.Lock()

    def cached(self, scenario: Scenario) -> ScenarioResult | None:
        path = self._cache_dir / live_cache_name(scenario, self._params)
        return load_result(path, scenario) if path.is_file() else None

    def run(self, scenario: Scenario) -> ScenarioResult:
        with self._lock:
            cached = self.cached(scenario)
            if cached is not None:
                return cached
            if self._bundle is None:
                self._bundle = load_bundle(self._data_dir)
            result = run_scenario(scenario, self._bundle, self._params)
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_dir / live_cache_name(scenario, self._params)
            partial = path.with_suffix(".tmp.npz")
            save_result(partial, result)
            partial.replace(path)
            return result


class ScenarioStore:
    def __init__(self, package: ScenarioPackage | None, live: LiveSimulator | None) -> None:
        self.package = package
        self.live = live

    def get(self, scenario: Scenario) -> StoredResult:
        seed = scenario_seed(scenario.key)
        if self.package is not None and scenario in self.package:
            return StoredResult(
                self.package.load(scenario), ResultSource.PRECOMPUTED, seed, self.package.version
            )
        if self.live is None:
            raise PackageError(
                f"Senaryo hazır pakette yok ve canlı simülasyon kapalı: {scenario.key}"
            )
        return StoredResult(self.live.run(scenario), ResultSource.LIVE, seed, None)
