"""Hazır senaryo paketinin dağıtımı: arşiv, kurulum ve bütünlük."""

import zipfile
from pathlib import Path

import numpy as np
import pytest

from sinek.connectome.download import IntegrityError, sha256_of
from sinek.connectome.sources import DataSource
from sinek.simulation.distribution import (
    build_archive,
    fetch_package,
    install_archive,
    package_dir,
    package_ready,
)
from sinek.simulation.params import LIFParams
from sinek.simulation.precompute import ScenarioResult, save_result, write_manifest
from sinek.simulation.scenarios import scenario_set
from sinek.simulation.store import PackageError


def _paket(kok: Path) -> Path:
    """225 senaryoluk küçük (sahte içerikli) ama biçimce geçerli bir paket."""
    dizin = package_dir(kok)
    dizin.mkdir(parents=True)
    for i, senaryo in enumerate(scenario_set()):
        save_result(
            dizin / f"{senaryo.key}.npz",
            ScenarioResult(
                scenario=senaryo,
                n_trials=30,
                t_run_ms=1000.0,
                indices=np.array([i], dtype=np.int32),
                count_sum=np.array([i + 1], dtype=np.int64),
                count_sq=np.array([(i + 1) ** 2], dtype=np.int64),
                fingerprint=f"test-{i}",
            ),
        )
    write_manifest(dizin, scenario_set(), LIFParams(), kok)
    return dizin


@pytest.fixture
def kaynak(tmp_path: Path) -> Path:
    return _paket(tmp_path / "kaynak")


def test_arsiv_deterministiktir(kaynak: Path, tmp_path: Path) -> None:
    a = build_archive(kaynak, tmp_path / "a.zip")
    b = build_archive(kaynak, tmp_path / "b.zip")

    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as arsiv:
        adlar = arsiv.namelist()
        assert adlar == sorted(adlar)
        assert "manifest.json" in adlar
        assert len(adlar) == len(scenario_set()) + 1
        assert {i.date_time for i in arsiv.infolist()} == {(1980, 1, 1, 0, 0, 0)}


def test_arsiv_kurulur_ve_dogrulanir(kaynak: Path, tmp_path: Path) -> None:
    arsiv = build_archive(kaynak, tmp_path / "paket.zip")
    hedef = tmp_path / "kullanici"

    kurulan = install_archive(arsiv, hedef)

    assert package_ready(hedef)
    for dosya in kaynak.iterdir():
        assert sha256_of(kurulan / dosya.name) == sha256_of(dosya)


def test_bozuk_dosya_iceren_arsiv_reddedilir_ve_mevcut_paket_korunur(
    kaynak: Path, tmp_path: Path
) -> None:
    hedef = tmp_path / "kullanici"
    install_archive(build_archive(kaynak, tmp_path / "iyi.zip"), hedef)

    kotu = tmp_path / "kotu.zip"
    with (
        zipfile.ZipFile(build_archive(kaynak, tmp_path / "gecici.zip")) as iyi,
        zipfile.ZipFile(kotu, "w") as yeni,
    ):
        for bilgi in iyi.infolist():
            veri = iyi.read(bilgi)
            if bilgi.filename.startswith("kontrol"):
                veri = veri[:-10] + b"0123456789"  # içerik değişti, özet tutmaz
            yeni.writestr(bilgi, veri)

    with pytest.raises(PackageError, match="bozuk"):
        install_archive(kotu, hedef)

    assert package_ready(hedef)  # eski sağlam paket yerinde


def test_dizin_disina_yazmaya_calisan_arsiv_reddedilir(tmp_path: Path) -> None:
    kotu = tmp_path / "kotu.zip"
    with zipfile.ZipFile(kotu, "w") as arsiv:
        arsiv.writestr("../../kacak.txt", b"x")

    with pytest.raises(PackageError, match="beklenmeyen yol"):
        install_archive(kotu, tmp_path / "kullanici")

    assert not (tmp_path / "kacak.txt").exists()


def test_eksik_paket_arsivlenmez(tmp_path: Path) -> None:
    with pytest.raises(PackageError):
        build_archive(tmp_path / "yok", tmp_path / "a.zip")


def test_paket_hazirsa_indirilmez(kaynak: Path, tmp_path: Path) -> None:
    kok = kaynak.parent.parent  # artifacts kökü
    sahte = DataSource("x", "x.zip", "https://ornek.invalid/x.zip", "0" * 64, 1, "", "", (1,))

    assert fetch_package(kok, source=sahte) == kaynak  # ağa hiç çıkılmadı


def test_indirilen_arsivin_ozeti_tutmazsa_kurulmaz(
    kaynak: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arsiv = build_archive(kaynak, tmp_path / "paket.zip")
    kaynak_dosya = DataSource(
        "s", "paket.zip", arsiv.resolve().as_uri(), "f" * 64, arsiv.stat().st_size, "", "", (1,)
    )

    with pytest.raises(IntegrityError):
        fetch_package(tmp_path / "kullanici", source=kaynak_dosya)

    assert not package_ready(tmp_path / "kullanici")


def test_indirilen_arsiv_kurulur(kaynak: Path, tmp_path: Path) -> None:
    arsiv = build_archive(kaynak, tmp_path / "paket.zip")
    kaynak_dosya = DataSource(
        "s",
        "paket.zip",
        arsiv.resolve().as_uri(),
        sha256_of(arsiv),
        arsiv.stat().st_size,
        "",
        "",
        (1,),
    )

    kurulan = fetch_package(tmp_path / "kullanici", source=kaynak_dosya)

    assert package_ready(tmp_path / "kullanici")
    assert not (tmp_path / "kullanici" / "indirilenler" / "paket.zip").exists()
    assert kurulan == package_dir(tmp_path / "kullanici")
