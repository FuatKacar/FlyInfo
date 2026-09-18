import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_env_ornegi_bos_anahtarlari_kabul_eder(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text("# yorum\nSINEK_GEMINI_API_KEY=\nSINEK_GEMINI_MODEL=gemini-2.5-flash\n")

    assert load_script("check_env_example").find_leaks(env) == []


def test_env_ornegi_dolu_anahtari_yakalar(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text("SINEK_GEMINI_API_KEY=sahte-anahtar\nSINEK_GROQ_API_KEY = baska\n")

    leaks = load_script("check_env_example").find_leaks(env)

    assert len(leaks) == 2
    assert all("sahte-anahtar" not in leak for leak in leaks)


def test_depodaki_env_ornegi_temiz() -> None:
    env = SCRIPTS.parent / ".env.example"

    assert load_script("check_env_example").find_leaks(env) == []


def test_kaynakca_basliklari_normalize_edilir() -> None:
    normalize = load_script("check_references").normalize

    assert normalize("Neuronal Control of\n <i>Drosophila</i> Walking") == normalize(
        "Neuronal control of Drosophila walking"
    )


def test_arayuz_kaynakcasi_bib_dosyasiyla_guncel() -> None:
    module = load_script("kaynakca_aktar")

    assert module.OUTPUT.read_text(encoding="utf-8") == module.render()
    numbers = [e["number"] for e in module.entries(module.BIB_PATH.read_text(encoding="utf-8"))]
    assert numbers == list(range(1, len(numbers) + 1))


def test_arayuz_api_semasi_guncel() -> None:
    module = load_script("openapi_aktar")

    expected = json.dumps(module.schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert module.OUTPUT.read_text(encoding="utf-8") == expected
