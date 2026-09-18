"""Yeniden üretilen yayınlanmış deneyler (Shiu et al. 2024, FlyWire v630).

Frekanslar ve susturulan nöronlar, her şeklin tüm aralığını kapsayacak şekilde seçilmiştir.
Susturma deneylerinde MN9'u en çok azaltan, en çok artıran ve etkisiz olan nöronlar bulunur.
"""

from dataclasses import dataclass, field
from typing import Literal

MN9_V630 = 720575940660219265  # referans kodundaki MN9 (sol, v630)

# Susturma deneylerinde v783'te kimliği değişen nöronların ardılları.
# Kaynak: FlyWire CAVE flywire_fafb_public, 2026-09-17 (get_latest_roots, L2 parça örtüşmesi).
V783_SILENCING_SUCCESSORS: dict[int, int] = {
    720575940615041430: 720575940640589171,  # DNge031; eski hacmin %100'ü
}


@dataclass(frozen=True)
class ReferenceExperiment:
    key: str
    figure: str
    title_tr: str
    stimuli: tuple[tuple[str, float], ...]  # (grup anahtarı, Hz)
    table: str  # referans oran tablosu (std tablosu `_rate` → `_rate_std`)
    column: str  # tüm beyin: sütun adı; tek nöron: satır (exp_name) adı
    kind: Literal["whole_brain", "single_neuron"]
    readout_id: int | None = None
    silenced_ids: tuple[int, ...] = field(default=())

    @property
    def std_table(self) -> str:
        return self.table.replace("_rate.csv", "_rate_std.csv")


def _sugar_brain(hz: int) -> ReferenceExperiment:
    return ReferenceExperiment(
        key=f"fig1d_sugar_{hz}hz",
        figure="1D",
        title_tr=f"Şekere duyarlı GRN'ler {hz} Hz → tüm beyin",
        stimuli=(("sugar", hz),),
        table="results/figure_1/fig_1d_rate.csv",
        column=f"sugarR_{hz}Hz",
        kind="whole_brain",
    )


def _water_brain(hz: int) -> ReferenceExperiment:
    return ReferenceExperiment(
        key=f"fig4a_water_{hz}hz",
        figure="4A",
        title_tr=f"Suya duyarlı GRN'ler {hz} Hz → tüm beyin",
        stimuli=(("water", hz),),
        table="results/figure_4/fig_4a_rate.csv",
        column=f"waterR_{hz}Hz",
        kind="whole_brain",
    )


def _jo_brain(hz: int) -> ReferenceExperiment:
    return ReferenceExperiment(
        key=f"fig5b_jo_{hz}hz",
        figure="5B",
        title_tr=f"Johnston organı nöronları {hz} Hz → tüm beyin",
        stimuli=(("johnston_organ", hz),),
        table="results/figure_5/fig_5b_rate.csv",
        column=f"JON_All_{hz}Hz",
        kind="whole_brain",
    )


def _sugar_bitter(sugar: int, bitter: int) -> ReferenceExperiment:
    stimuli: tuple[tuple[str, float], ...] = (("sugar", sugar), ("bitter", bitter))
    return ReferenceExperiment(
        key=f"fig3a_sugar{sugar}_bitter{bitter}",
        figure="3A",
        title_tr=f"Şeker {sugar} Hz + acı {bitter} Hz → MN9",
        stimuli=stimuli,
        table="results/figure_3/fig_3a_rate.csv",
        column=f"Sugar_Bitter_{sugar}_Hz_{bitter}_Hz",
        kind="single_neuron",
        readout_id=MN9_V630,
    )


def _silencing(neuron_id: int) -> ReferenceExperiment:
    return ReferenceExperiment(
        key=f"fig1f_silence_{neuron_id}",
        figure="1F",
        title_tr=f"Şeker 100 Hz, {neuron_id} susturuldu → MN9",
        stimuli=(("sugar", 100),),
        table="results/figure_1/fig_1f_100_hz_rate.csv",
        column=f"sugarR-silencing{neuron_id}_100_Hz",
        kind="single_neuron",
        readout_id=MN9_V630,
        silenced_ids=(neuron_id,),
    )


EXPERIMENTS: tuple[ReferenceExperiment, ...] = (
    *(_sugar_brain(hz) for hz in (40, 80, 120, 160, 200)),
    *(_water_brain(hz) for hz in (100, 180, 260)),
    *(_jo_brain(hz) for hz in (60, 140, 220)),
    *(_sugar_bitter(s, b) for s in (100, 200) for b in (0, 100, 200)),
    *(
        _silencing(i)
        for i in (
            720575940623211725,  # referansta MN9'u en çok azaltan
            720575940607272649,  # güçlü azaltma
            720575940606866377,  # etkisiz (medyana yakın)
            720575940612906518,  # artırma
            720575940615041430,  # referansta MN9'u en çok artıran
        )
    ),
)
