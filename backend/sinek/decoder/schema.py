"""Çözümleyici çıktı sözleşmesi.

Bu şema, simülasyon ile sunum katmanı (şablon metin / LLM) ve API arasındaki TEK arayüzdür.
Sunum katmanı yalnızca bu yapıdaki bilgiyi dile getirebilir; doğrulayıcı üretilen metni buna
karşı denetler. Anahtarlar İngilizce ve ASCII'dir; kullanıcıya görünen etiketler `tr.json`'dan
gelir (yol haritası 0.1).
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sinek.connectome.groups import Behavior


class SimulationMode(StrEnum):
    PRECOMPUTED = "precomputed"  # hazır senaryo
    LIVE = "live"  # kullanıcının bilgisayarında canlı simülasyon


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class StimulusComponent(_Frozen):
    group: str  # neuron_groups.toml anahtarı ya da Laboratuvar seçim anahtarı
    name_tr: str  # kullanıcıya görünen ad
    # Sohbet senaryolarında yoğunluk (0-1]; Laboratuvar'da doğrudan frekans verildiği için boş olur.
    intensity: float | None = Field(default=None, gt=0, le=1)
    rate_hz: float = Field(gt=0)
    neuron_count: int = Field(ge=1)


class StimulusInfo(_Frozen):
    components: tuple[StimulusComponent, ...]  # boşsa uyarım yok (kontrol / kapsam dışı)
    match_score: float | None = Field(default=None, ge=0, le=1)  # yalnızca Sohbet
    scenario_key: str


class BehaviorReadout(_Frozen):
    behavior: Behavior
    readout_group: str  # neuron_groups.toml okuma grubu
    rate_hz: float = Field(ge=0)  # okuma nöronları arasında en yüksek ateşleme hızı
    rate_std_hz: float = Field(ge=0)  # o nöronun denemeler arası standart sapması (ddof=0)
    # kalibre edilmiş skor; kalibrasyon verisi yoksa None (bkz. docs/cozumleyici.md)
    score: float | None = Field(default=None, ge=0, le=1)
    active: bool


class NeuropilActivity(_Frozen):
    neuropil: str  # FlyWire nöropil adı (ör. GNG, PRW, AL_L)
    events_hz: float = Field(ge=0)  # tahmini sinaptik çıkış olayı / sn
    share: float = Field(ge=0, le=1)  # tüm nöropillerin toplamı içindeki pay


class ModelInfo(_Frozen):
    type: Literal["LIF"] = "LIF"
    dataset: Literal["FlyWire v783"] = "FlyWire v783"
    sign_source: Literal["reference", "annotations"] = "reference"
    mode: SimulationMode
    n_trials: int = Field(ge=1)
    t_run_ms: float = Field(gt=0)
    seed: int
    package_version: str | None = None  # hazır senaryolarda veri paketi sürümü


class DecoderOutput(_Frozen):
    stimulus: StimulusInfo
    behaviors: tuple[BehaviorReadout, ...]
    circuit_only: bool  # uyarımın çözümleyicide doğrudan davranış karşılığı yok (ör. CO₂)
    top_neuropils: tuple[NeuropilActivity, ...]
    active_neuron_count: int = Field(ge=0)
    model: ModelInfo

    @property
    def active_behaviors(self) -> tuple[BehaviorReadout, ...]:
        return tuple(b for b in self.behaviors if b.active)
