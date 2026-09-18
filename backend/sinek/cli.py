"""FlyInfo `sinek` komut satırı giriş noktası.

sinek              eksik veriyi indirir ve sunucuyu başlatır (varsayılan)
sinek baslat       aynı
sinek indir        ham veriyi ve hazır senaryo paketini indirir, doğrular, özet rapor verir
sinek dogrula      modeli yayınlanmış sonuçlarla karşılaştırır, docs/dogrulama.md üretir
sinek hesapla      senaryo setini önceden hesaplar (kaldığı yerden devam eder)
sinek paketle      hazır senaryo paketini yayın arşivine yazar (bakımcılar için)
"""

import argparse
import sys
import threading
import webbrowser
from typing import TYPE_CHECKING

from sinek import __version__
from sinek.config import get_settings

if TYPE_CHECKING:
    from sinek.connectome.sources import DataSource


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="sinek", description="FlyInfo — Drosophila beyin simülasyonu"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="komut")

    start = commands.add_parser("baslat", help="Sunucuyu başlatır (varsayılan komut)")
    start.add_argument("--host", default=settings.host, help="Dinlenecek adres")
    start.add_argument("--port", type=int, default=settings.port, help="Dinlenecek port")
    start.add_argument(
        "--tarayici-acma",
        dest="open_browser",
        action="store_false",
        help="Sunucu başladığında tarayıcıyı otomatik açma",
    )

    commands.add_parser(
        "indir", help="Ham veriyi ve hazır senaryo paketini indirir, doğrular, özet rapor verir"
    )
    commands.add_parser(
        "dogrula",
        help="Modeli Shiu et al. (2024) sonuçlarıyla karşılaştırır ve doğrulama raporunu üretir",
    )
    commands.add_parser(
        "hesapla", help="Senaryo setini önceden hesaplar; yarıda kalırsa kaldığı yerden devam eder"
    )
    commands.add_parser(
        "paketle", help="Hazır senaryo paketini GitHub Release arşivine yazar (bakımcılar için)"
    )
    parser.set_defaults(command="baslat", host=settings.host, port=settings.port, open_browser=True)
    return parser


def _progress_bar(source: "DataSource", received: int, total: int) -> None:
    percent = 100 * received // total if total else 100
    sys.stdout.write(f"\r  {source.filename}: %{percent:3d}")
    if received >= total:
        sys.stdout.write("\n")
    sys.stdout.flush()


def _ensure_package() -> None:
    """Hazır senaryo paketi yoksa GitHub Release'ten indirir; indirilemezse nedenini söyler."""
    import urllib.error

    from sinek.simulation.distribution import SCENARIO_ARCHIVE, fetch_package, package_ready

    settings = get_settings()
    if package_ready(settings.artifacts_dir):
        return
    print(f"Hazır senaryo paketi indiriliyor ({SCENARIO_ARCHIVE.size / 1e6:.1f} MB)…")
    try:
        path = fetch_package(settings.artifacts_dir, progress=_progress_bar)
    except (urllib.error.URLError, OSError, ValueError) as error:
        print(
            f"  Paket indirilemedi ({error}).\n"
            "  Uygulama yine çalışır, ancak her mesaj bilgisayarınızda canlı simüle edilir "
            "(ekran kartıyla ~1,5 dk).\n"
            "  Paketi kendiniz üretmek için: uv run sinek hesapla (~5 saat, ekran kartıyla)"
        )
        return
    print(f"  Paket kuruldu ve doğrulandı: {path}")


def _ensure_data() -> None:
    """Uygulamanın ihtiyaç duyduğu ham veri eksikse indirir (tek komutla çalıştırma)."""
    from sinek.connectome.download import is_valid
    from sinek.connectome.pipeline import raw_dir
    from sinek.connectome.sources import SOURCES

    raw = raw_dir(get_settings().data_dir)
    if not all(is_valid(raw / s.filename, s) for s in SOURCES):
        print("FlyWire verisi eksik; indiriliyor (ilk çalıştırmada bir kez, ~150 MB)…")
        _run_download(report=False)
        return
    _ensure_package()


def _run_server(host: str, port: int, open_browser: bool) -> None:
    import uvicorn

    _ensure_data()
    url = f"http://{host}:{port}"
    print(f"FlyInfo {__version__} başlatılıyor: {url}")
    if open_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run("sinek.api.app:create_app", factory=True, host=host, port=port)


def _run_download(report: bool = True) -> None:
    from sinek.connectome.pipeline import format_report, prepare

    data_dir = get_settings().data_dir
    print(f"Veri dizini: {data_dir.resolve()}")
    bundle = prepare(data_dir, progress=_progress_bar)
    print("Tüm dosyalar SHA-256 ile doğrulandı.")
    _ensure_package()
    if report:
        print()
        print(format_report(bundle))


def _run_packaging() -> None:
    from pathlib import Path

    from sinek.simulation.distribution import (
        ARCHIVE_NAME,
        SCENARIO_ARCHIVE,
        build_archive,
        describe_archive,
        package_dir,
    )

    archive = build_archive(package_dir(get_settings().artifacts_dir), Path("dist") / ARCHIVE_NAME)
    size, digest = describe_archive(archive)
    print(f"Arşiv: {archive.resolve()}\n  boyut  : {size}\n  sha256 : {digest}")
    if (size, digest) == (SCENARIO_ARCHIVE.size, SCENARIO_ARCHIVE.sha256):
        print("Koddaki SCENARIO_ARCHIVE sabitleriyle aynı; yayımlanabilir.")
    else:
        print(
            "UYARI: Koddaki SCENARIO_ARCHIVE sabitlerinden farklı; "
            "backend/sinek/simulation/distribution.py dosyasını güncelleyin."
        )


def _run_validation() -> None:
    import time
    from pathlib import Path

    try:
        from sinek.validation.report import write_report
    except ImportError:
        sys.exit("Doğrulama bağımlılıkları eksik: uv sync --group validation")
    from sinek.simulation.params import LIFParams
    from sinek.validation.experiments import ReferenceExperiment
    from sinek.validation.run import ExperimentStatus, run_validation

    settings = get_settings()
    start = time.monotonic()
    labels = {
        "basliyor": "başlıyor",
        "hesaplandi": "hesaplandı",
        "onbellekten": "önbellekten",
        "atlandi": "atlandı",
    }

    def report(
        number: int, total: int, experiment: ReferenceExperiment, status: ExperimentStatus
    ) -> None:
        elapsed = time.monotonic() - start
        print(f"[{elapsed:6.0f} sn] {number:2d}/{total} {labels[status]:12} {experiment.title_tr}")

    params = LIFParams()
    results = {}
    for dataset in ("v630", "v783"):
        print(f"\n== {dataset} ==")
        results[dataset] = run_validation(
            settings.data_dir,
            settings.data_dir / "validation" / dataset,
            params,
            on_experiment=report,
            dataset=dataset,
        )
    path = write_report(results["v630"], results["v783"], params, Path("docs"))
    print(f"\nRapor yazıldı: {path}")


def _run_precompute() -> None:
    import time

    from sinek.connectome.pipeline import prepare
    from sinek.simulation.precompute import PACKAGE_VERSION, precompute
    from sinek.simulation.scenarios import Scenario, scenario_set

    settings = get_settings()
    scenarios = scenario_set()
    package_dir = settings.artifacts_dir / "scenarios" / PACKAGE_VERSION
    print(f"{len(scenarios)} senaryo → {package_dir.resolve()}")
    bundle = prepare(settings.data_dir)
    start = time.monotonic()
    labels = {"mevcut": "mevcut", "basliyor": "başlıyor", "hesaplandi": "hesaplandı"}

    def report(number: int, total: int, scenario: Scenario, status: str) -> None:
        elapsed = time.monotonic() - start
        line = f"[{elapsed:7.0f} sn] {number:3d}/{total} {labels[status]:10} {scenario.key}"
        print(line, flush=True)

    manifest = precompute(scenarios, bundle, package_dir, settings.data_dir, progress=report)
    print(f"\nManifest yazıldı: {manifest}")


def _use_utf8_console() -> None:
    """Windows konsolunun eski kod sayfası (ör. cp1254) Türkçe/bilimsel karakterlerde çökmesin."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> None:
    _use_utf8_console()
    args = build_parser().parse_args(argv)
    if args.command == "indir":
        _run_download()
    elif args.command == "dogrula":
        _run_validation()
    elif args.command == "hesapla":
        _run_precompute()
    elif args.command == "paketle":
        _run_packaging()
    else:
        _run_server(args.host, args.port, args.open_browser)


if __name__ == "__main__":
    main()
