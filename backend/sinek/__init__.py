"""FlyInfo: Drosophila konektomu üzerinde şeffaf beyin simülasyonu."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("flyinfo")
except PackageNotFoundError:  # paket kurulmadan kaynak koddan çalıştırıldığında
    __version__ = "0.0.0+yerel"

__all__ = ["__version__"]
