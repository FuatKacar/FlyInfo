import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from sinek.connectome.download import IntegrityError, download
from sinek.connectome.sources import COMPLETENESS, SOURCES, DataSource


def local_source(tmp_path: Path, content: bytes, sha256: str | None = None) -> DataSource:
    origin = tmp_path / "kaynak.csv"
    origin.write_bytes(content)
    return replace(
        COMPLETENESS,
        url=origin.as_uri(),
        size=len(content),
        sha256=sha256 or hashlib.sha256(content).hexdigest(),
    )


def test_indirir_dogrular_ve_ilerleme_bildirir(tmp_path: Path) -> None:
    source = local_source(tmp_path, b"veri" * 1000)
    calls: list[int] = []

    path = download(source, tmp_path / "raw", progress=lambda _s, got, _t: calls.append(got))

    assert path.read_bytes() == b"veri" * 1000
    assert calls[-1] == 4000


def test_gecerli_dosya_yeniden_indirilmez(tmp_path: Path) -> None:
    source = local_source(tmp_path, b"veri")
    download(source, tmp_path / "raw")
    (tmp_path / "kaynak.csv").unlink()  # kaynak artık yok; indirme denenirse hata verir

    assert download(source, tmp_path / "raw").read_bytes() == b"veri"


def test_ozet_uyusmazsa_dosya_birakilmaz(tmp_path: Path) -> None:
    source = local_source(tmp_path, b"veri", sha256="0" * 64)

    with pytest.raises(IntegrityError):
        download(source, tmp_path / "raw")

    assert list((tmp_path / "raw").iterdir()) == []


def test_kaynaklar_sabitlenmis_ve_benzersiz() -> None:
    assert len({s.key for s in SOURCES}) == len(SOURCES)
    for source in SOURCES:
        assert len(source.sha256) == 64
        # Değişmez kaynaklara sabitlenmeli: git commit'i ya da sürümlü Zenodo kaydı (dal değil)
        pinned_github = source.url.startswith("https://raw.githubusercontent.com/") and (
            "/main/" not in source.url
        )
        pinned_zenodo = source.url.startswith("https://zenodo.org/records/")
        assert pinned_github or pinned_zenodo, source.url
        assert source.citations
