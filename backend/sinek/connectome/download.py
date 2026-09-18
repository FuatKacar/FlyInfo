"""Ham verinin indirilmesi ve bütünlük doğrulaması."""

import hashlib
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path

from sinek.connectome.sources import SOURCES, DataSource

ProgressCallback = Callable[[DataSource, int, int], None]

_CHUNK = 1 << 20
_USER_AGENT = "flyinfo (+https://github.com/FuatKacar/FlyInfo)"


class IntegrityError(RuntimeError):
    """İndirilen dosyanın özeti beklenen değerle eşleşmedi."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def is_valid(path: Path, source: DataSource) -> bool:
    return (
        path.is_file() and path.stat().st_size == source.size and sha256_of(path) == source.sha256
    )


def download(
    source: DataSource, target_dir: Path, progress: ProgressCallback | None = None
) -> Path:
    """Dosyayı indirir; zaten geçerli bir kopya varsa yeniden indirmez.

    İndirme önce `.part` dosyasına yapılır ve yalnızca özet doğrulanırsa yerine taşınır.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.filename
    if is_valid(target, source):
        return target

    partial = target.with_name(target.name + ".part")
    request = urllib.request.Request(source.url, headers={"User-Agent": _USER_AGENT})
    digest = hashlib.sha256()
    received = 0
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as file:
        while chunk := response.read(_CHUNK):
            file.write(chunk)
            digest.update(chunk)
            received += len(chunk)
            if progress:
                progress(source, received, source.size)

    if received != source.size or digest.hexdigest() != source.sha256:
        partial.unlink(missing_ok=True)
        raise IntegrityError(
            f"{source.filename} doğrulanamadı: beklenen {source.size} bayt / {source.sha256}, "
            f"alınan {received} bayt / {digest.hexdigest()}"
        )
    partial.replace(target)
    return target


def download_all(
    target_dir: Path,
    sources: Iterable[DataSource] = SOURCES,
    progress: ProgressCallback | None = None,
) -> dict[str, Path]:
    return {source.key: download(source, target_dir, progress) for source in sources}
