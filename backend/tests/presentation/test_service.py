from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sinek.config import Settings
from sinek.decoder.schema import DecoderOutput
from sinek.presentation.providers import ProviderError, providers_from_settings
from sinek.presentation.service import PresentationService
from sinek.presentation.template import render_template

FAITHFUL = "Şekere duyarlı 21 tat nöronum 160 Hz ile uyarıldı; beslenme devrem %82 etkin."
UNFAITHFUL = "Bala bayıldım ve çok mutlu oldum; beslenme devrem %99 etkin."


@dataclass
class FakeProvider:
    replies: list[str | Exception]
    name: str = "sahte"
    model: str = "m1"
    calls: list[str] = field(default_factory=list)

    def generate(self, system: str, content: str) -> str:
        self.calls.append(content)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_llm_kapaliyken_sablon(sugar_output: DecoderOutput) -> None:
    result = PresentationService([], cache_dir=None).present(sugar_output)

    assert result.source == "template"
    assert result.text == render_template(sugar_output)


def test_sadik_yanit_kabul_edilir_ve_kullanici_mesaji_gonderilmez(
    sugar_output: DecoderOutput,
) -> None:
    provider = FakeProvider([FAITHFUL])

    result = PresentationService([provider], cache_dir=None).present(sugar_output)

    assert (result.source, result.text) == ("llm", FAITHFUL)
    assert '"scenario_key": "sugar@0.8"' in provider.calls[0]  # yalnızca çözümleyici JSON'u
    assert '"seed"' not in provider.calls[0]


def test_sadakatsiz_yanit_reddedilir_yedek_saglayici_denenir(sugar_output: DecoderOutput) -> None:
    first = FakeProvider([UNFAITHFUL], name="birincil")
    second = FakeProvider([FAITHFUL], name="yedek")

    result = PresentationService([first, second], cache_dir=None).present(sugar_output)

    assert result.provider == "yedek"
    assert result.text == FAITHFUL


def test_tum_saglayicilar_basarisizsa_sablon_ve_neden(sugar_output: DecoderOutput) -> None:
    providers = [
        FakeProvider([ProviderError("kota doldu")], name="a"),
        FakeProvider([UNFAITHFUL], name="b"),
    ]

    result = PresentationService(providers, cache_dir=None).present(sugar_output)

    assert result.source == "template"
    assert result.fallback_reason is not None
    assert "kota doldu" in result.fallback_reason
    assert "yasak ifade" in result.fallback_reason


def test_gecerli_yanit_onbellege_alinir(sugar_output: DecoderOutput, tmp_path: Path) -> None:
    provider = FakeProvider([FAITHFUL])
    service = PresentationService([provider], cache_dir=tmp_path)

    service.present(sugar_output)
    again = service.present(sugar_output)

    assert again.text == FAITHFUL
    assert len(provider.calls) == 1  # ikinci istekte API çağrılmadı


def test_bozuk_onbellek_kullanilmaz(sugar_output: DecoderOutput, tmp_path: Path) -> None:
    provider = FakeProvider([FAITHFUL, FAITHFUL])
    service = PresentationService([provider], cache_dir=tmp_path)
    service.present(sugar_output)
    (cached,) = (tmp_path / "llm").iterdir()
    cached.write_text(UNFAITHFUL, encoding="utf-8")

    result = service.present(sugar_output)

    assert result.text == FAITHFUL
    assert len(provider.calls) == 2


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, []),
        ({"SINEK_LLM_PROVIDER": "gemini"}, []),  # anahtar yok
        (
            {"SINEK_LLM_PROVIDER": "gemini", "SINEK_GEMINI_API_KEY": "x"},
            [("gemini", "gemini-3.8-flash"), ("gemini", "gemini-3.5-flash-lite")],
        ),
        (
            {"SINEK_LLM_PROVIDER": "groq", "SINEK_GROQ_API_KEY": "x"},
            [("groq", "llama-3.3-70b-versatile")],
        ),
        ({"SINEK_LLM_PROVIDER": "ollama"}, [("ollama", "qwen3")]),
    ],
)
def test_saglayici_secimi(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], expected: list[tuple[str, str]]
) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    providers = providers_from_settings(Settings())

    assert [(p.name, p.model) for p in providers] == expected
