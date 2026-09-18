import pytest

from sinek import __version__
from sinek.cli import build_parser


def test_komutsuz_cagri_sunucuyu_baslatir() -> None:
    args = build_parser().parse_args([])

    assert args.command == "baslat"
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.open_browser is True


def test_baslat_bayraklari() -> None:
    args = build_parser().parse_args(["baslat", "--tarayici-acma", "--port", "9000"])

    assert args.command == "baslat"
    assert args.open_browser is False
    assert args.port == 9000


def test_indir_komutu() -> None:
    assert build_parser().parse_args(["indir"]).command == "indir"


def test_surum_bayragi(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])

    assert __version__ in capsys.readouterr().out


def test_dogrula_komutu() -> None:
    assert build_parser().parse_args(["dogrula"]).command == "dogrula"


def test_hesapla_komutu() -> None:
    assert build_parser().parse_args(["hesapla"]).command == "hesapla"


def test_paketle_komutu() -> None:
    assert build_parser().parse_args(["paketle"]).command == "paketle"


def test_baslatmadan_once_eksik_veri_indirilir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tek komutla çalıştırma: veri eksikse sunucudan önce indirme yapılır."""
    from sinek import cli

    cagrilar: list[str] = []
    monkeypatch.setattr(cli, "_ensure_data", lambda: cagrilar.append("veri"))
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: cagrilar.append("sunucu"))

    cli._run_server("127.0.0.1", 8000, open_browser=False)

    assert cagrilar == ["veri", "sunucu"]


def test_paket_indirilemezse_uygulama_yine_baslar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import urllib.error

    from sinek import cli

    def indirme_hatasi(*_a: object, **_k: object) -> None:
        raise urllib.error.HTTPError("https://ornek", 404, "Not Found", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr("sinek.simulation.distribution.package_ready", lambda _d: False)
    monkeypatch.setattr("sinek.simulation.distribution.fetch_package", indirme_hatasi)

    cli._ensure_package()  # hata fırlatmaz

    cikti = capsys.readouterr().out
    assert "indirilemedi" in cikti
    assert "sinek hesapla" in cikti
