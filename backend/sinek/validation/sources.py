"""Doğrulama verisi: makalenin kullandığı FlyWire v630 konektomu ve yayınlanmış sonuç tabloları.

Sonuç tabloları Edmond arşivindeki 4,5 GB'lık `results.zip` içindedir. Arşivin tamamı indirilmez:
HTTP aralık (Range) istekleriyle yalnızca zip dizini ve gereken küçük tablolar okunur.
Her tablo SHA-256 ile doğrulanır.
"""

import io
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from sinek.connectome.download import sha256_of
from sinek.connectome.sources import SHIU_COMMIT, DataSource

_SHIU_RAW = f"https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/{SHIU_COMMIT}"

V630_COMPLETENESS = DataSource(
    key="completeness_630",
    filename="2023_03_23_completeness_630_final.csv",
    url=f"{_SHIU_RAW}/2023_03_23_completeness_630_final.csv",
    sha256="e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb",
    size=3_057_611,
    description="FlyWire v630 nöron listesi (makalede kullanılan sürüm)",
    license="MIT (kod deposu) / CC-BY 4.0 (FlyWire verisi)",
    citations=(1, 3),
)

V630_CONNECTIVITY = DataSource(
    key="connectivity_630",
    filename="2023_03_23_connectivity_630_final.parquet",
    url=f"{_SHIU_RAW}/2023_03_23_connectivity_630_final.parquet",
    sha256="94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3",
    size=86_630_944,
    description="FlyWire v630 işaretli bağlantı tablosu (makalede kullanılan sürüm)",
    license="MIT (kod deposu) / CC-BY 4.0 (FlyWire verisi)",
    citations=(1, 3, 4),
)

V630_SOURCES: tuple[DataSource, ...] = (V630_COMPLETENESS, V630_CONNECTIVITY)

RESULTS_DOI = "10.17617/3.CZODIW"
RESULTS_ARCHIVE_URL = "https://edmond.mpg.de/api/access/datafile/223847"  # results.zip, sürüm 3


@dataclass(frozen=True)
class ReferenceTable:
    member: str
    sha256: str
    size: int


REFERENCE_TABLES: tuple[ReferenceTable, ...] = tuple(
    ReferenceTable(member, sha, size)
    for member, (sha, size) in {
        "results/figure_1/fig_1d_rate.csv": (
            "4a88d643be66bfc686b36f8a10091621a5d2bb2c88fe04ca710ad97b7aba87de",
            123_742,
        ),
        "results/figure_1/fig_1d_rate_std.csv": (
            "eeca06c1eb98a21fff179b4b4e69c30f074a3a7a460e8a94e7343c1a12c8e252",
            154_265,
        ),
        "results/figure_4/fig_4a_rate.csv": (
            "91697a197ef996b791814b7bfa8b3407f823202eae028806adcfd2e5c1554821",
            66_244,
        ),
        "results/figure_4/fig_4a_rate_std.csv": (
            "c668a5446f28091963966b072f11de27f189729c49fbf117f13641ef8c9ca6f9",
            77_661,
        ),
        "results/figure_5/fig_5b_rate.csv": (
            "53ae8eb06b52b8d23c4a845af7267199a81065f88fbc6971012b8c15b298ea1c",
            120_827,
        ),
        "results/figure_5/fig_5b_rate_std.csv": (
            "c13895dd1da727d845c1233a329cd73f23ce05a33bf81dd9fc452497113cf0bd",
            144_144,
        ),
        "results/figure_3/fig_3a_rate.csv": (
            "fd7350b3b8da10b924818d0d5c9854ff3b871c48ea2701f867b0f67254d83566",
            4_617,
        ),
        "results/figure_3/fig_3a_rate_std.csv": (
            "48480e2b21ba22abb21c0a80219601f241af707546561cf7894225eb343e4b2e",
            4_972,
        ),
        "results/figure_1/fig_1f_100_hz_rate.csv": (
            "1b4830bd61ceeb65b478a7fac61c6e16984da30eba03a27768cf639c18a98897",
            11_234,
        ),
        "results/figure_1/fig_1f_100_hz_rate_std.csv": (
            "2525db5a9d7cf0d4f201909916886129a0288768795961524cf1e3a00b21b058",
            12_243,
        ),
    }.items()
)


class _HttpRangeReader(io.RawIOBase):
    """Uzak dosyayı HTTP Range istekleriyle rastgele erişimli okur."""

    def __init__(self, url: str) -> None:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=60) as response:
            self._url = response.geturl()  # imzalı nesne deposu adresine yönlendirme
            self._size = int(response.headers["Content-Length"])
        self._pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence]
        self._pos = base + offset
        return self._pos

    def readinto(self, buffer: memoryview) -> int:  # type: ignore[override]
        if self._pos >= self._size:
            return 0
        end = min(self._pos + len(buffer), self._size) - 1
        request = urllib.request.Request(self._url, headers={"Range": f"bytes={self._pos}-{end}"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        buffer[: len(data)] = data
        self._pos += len(data)
        return len(data)


def reference_dir(data_dir: Path) -> Path:
    return data_dir / "reference" / "shiu2024"


def fetch_reference_tables(data_dir: Path) -> None:
    """Eksik veya bozuk referans tablolarını arşivden çıkarır ve doğrular."""
    target = reference_dir(data_dir)
    needed = [
        t
        for t in REFERENCE_TABLES
        if not ((target / t.member).is_file() and sha256_of(target / t.member) == t.sha256)
    ]
    if not needed:
        return
    reader = io.BufferedReader(_HttpRangeReader(RESULTS_ARCHIVE_URL), buffer_size=1 << 16)
    with zipfile.ZipFile(reader) as archive:
        for table in needed:
            path = target / table.member
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(table.member))  # zipfile CRC-32'yi de denetler
            if sha256_of(path) != table.sha256:
                path.unlink()
                raise RuntimeError(f"Referans tablo doğrulanamadı: {table.member}")
