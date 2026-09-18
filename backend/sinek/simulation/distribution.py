"""Hazır senaryo paketinin dağıtımı: arşivleme, GitHub Release'ten indirme ve kurulum.

Paketin kendisini üretmek ekran kartında ~5 saat sürer (`sinek hesapla`). Kullanıcılar bunun
yerine aynı paketi GitHub Release'ten indirir; iki yol **birebir aynı** dosyaları verir (paketteki
her dosyanın SHA-256 özeti manifestte, arşivin özeti bu modülde sabittir).

Arşiv deterministiktir: dosyalar ada göre sıralanır, zaman damgaları sabittir ve sıkıştırma
uygulanmaz (`.npz` dosyaları zaten sıkıştırılmıştır). Aynı paket her zaman aynı baytları üretir.

Bakımcı için yayın adımları (README, "Yeni sürüm yayımlama"):
    uv run sinek paketle                 # dist/ altına arşivi yazar, boyut ve SHA-256 yazdırır
    # SCENARIO_ARCHIVE sabitlerini güncelle, ardından:
    gh release upload veri-v1 dist/flyinfo-senaryolar-1.zip
"""

import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path

from sinek.connectome.download import download, sha256_of
from sinek.connectome.sources import DataSource
from sinek.simulation.precompute import PACKAGE_VERSION
from sinek.simulation.scenarios import scenario_set
from sinek.simulation.store import PackageError, ScenarioPackage

RELEASE_TAG = f"veri-v{PACKAGE_VERSION}"
ARCHIVE_NAME = f"flyinfo-senaryolar-{PACKAGE_VERSION}.zip"
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)  # ZIP biçiminin izin verdiği en erken tarih

SCENARIO_ARCHIVE = DataSource(
    key="scenarios",
    filename=ARCHIVE_NAME,
    url=f"https://github.com/FuatKacar/FlyInfo/releases/download/{RELEASE_TAG}/{ARCHIVE_NAME}",
    sha256="0aca42a65259808089d19d0ea551c2c7dfef9ce248eca9bd1acb2aad8cef3950",
    size=7_765_209,
    description="Önceden hesaplanmış 225 senaryo (30 deneme × 1 sn, FlyWire v783)",
    license="CC-BY 4.0 (FlyWire verisinden türetilmiştir)",
    citations=(1, 2, 3),
)

ProgressCallback = Callable[[DataSource, int, int], None]


def package_dir(artifacts_dir: Path) -> Path:
    return artifacts_dir / "scenarios" / PACKAGE_VERSION


def _package_files(directory: Path) -> list[Path]:
    expected = {f"{s.key}.npz" for s in scenario_set()} | {"manifest.json"}
    present = {p.name for p in directory.iterdir() if p.is_file()} if directory.is_dir() else set()
    missing = expected - present
    if missing:
        raise PackageError(f"Paket eksik: {len(missing)} dosya yok (ör. {sorted(missing)[0]})")
    return sorted(directory / name for name in expected)


def build_archive(directory: Path, output: Path) -> Path:
    """Paketi deterministik bir zip arşivine yazar (aynı paket → aynı baytlar)."""
    ScenarioPackage.open(directory)  # yalnızca doğrulanmış paket arşivlenir
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(".part")
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in _package_files(directory):
            info = zipfile.ZipInfo(path.name, date_time=_FIXED_TIME)
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    partial.replace(output)
    return output


def install_archive(archive_path: Path, artifacts_dir: Path) -> Path:
    """Arşivi paket dizinine açar ve paketi tam doğrular; hata olursa mevcut paket korunur."""
    target = package_dir(artifacts_dir)
    staging = target.with_name(target.name + ".kurulum")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                name = Path(member.filename).name
                if name != member.filename or name.startswith("."):
                    raise PackageError(f"Arşivde beklenmeyen yol: {member.filename}")
                (staging / name).write_bytes(archive.read(member))
        package = ScenarioPackage.open(staging)
        for scenario in scenario_set():
            package.load(scenario)  # her dosyanın SHA-256'sı manifestle karşılaştırılır
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    backup = target.with_name(target.name + ".eski")
    shutil.rmtree(backup, ignore_errors=True)
    if target.exists():
        target.replace(backup)
    staging.replace(target)
    shutil.rmtree(backup, ignore_errors=True)
    return target


def package_ready(artifacts_dir: Path) -> bool:
    try:
        ScenarioPackage.open(package_dir(artifacts_dir))
    except PackageError:
        return False
    return True


def fetch_package(
    artifacts_dir: Path,
    progress: ProgressCallback | None = None,
    source: DataSource = SCENARIO_ARCHIVE,
) -> Path:
    """Paket yoksa GitHub Release'ten indirir, doğrular ve kurar."""
    if package_ready(artifacts_dir):
        return package_dir(artifacts_dir)
    archive = download(source, artifacts_dir / "indirilenler", progress=progress)
    installed = install_archive(archive, artifacts_dir)
    archive.unlink(missing_ok=True)
    return installed


def describe_archive(path: Path) -> tuple[int, str]:
    """Arşivin boyutu ve SHA-256 özeti (SCENARIO_ARCHIVE sabitlerini güncellemek için)."""
    return path.stat().st_size, sha256_of(path)
