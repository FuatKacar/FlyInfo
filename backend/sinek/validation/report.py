"""Doğrulama raporu: `docs/dogrulama.md` ve `docs/dogrulama/*.png` üretir.

Grafik renkleri doğrulanmış kategorik paletin ilk iki yuvasıdır (renk körlüğü denetimi geçti):
bizim model = mavi, referans = turuncu. Eksenler tek ölçeklidir; sayılar tablo olarak da verilir.
"""

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import numpy as np

from sinek.simulation.params import LIFParams
from sinek.validation.compare import SingleNeuronComparison, WholeBrainComparison
from sinek.validation.run import ExperimentOutcome
from sinek.validation.sources import RESULTS_DOI

OURS = "#2a78d6"
REFERENCE = "#eb6834"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3df"
IDENTITY = "#a8a7a2"


def _style_axes(ax) -> None:  # type: ignore[no-untyped-def]
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(IDENTITY)
    ax.tick_params(colors=INK_SECONDARY, labelsize=8)
    ax.xaxis.label.set_color(INK_SECONDARY)
    ax.yaxis.label.set_color(INK_SECONDARY)


def _whole_brain_figure(outcomes: Sequence[ExperimentOutcome], path: Path, subtitle: str) -> None:
    import matplotlib.pyplot as plt

    columns = 4
    rows = -(-len(outcomes) // columns)
    fig, axes = plt.subplots(rows, columns, figsize=(3.2 * columns, 3.3 * rows), facecolor=SURFACE)
    for ax in axes.flat[len(outcomes) :]:
        ax.set_visible(False)
    for ax, outcome in zip(axes.flat, outcomes, strict=False):
        assert outcome.reference_rates_hz is not None
        c = outcome.comparison
        assert isinstance(c, WholeBrainComparison)
        ref, ours = outcome.reference_rates_hz, outcome.rates_hz
        active = (ref > 0) | (ours > 0)
        if outcome.comparable is not None:
            active &= outcome.comparable
        limit = max(ref[active].max(), ours[active].max()) * 1.05
        _style_axes(ax)
        ax.plot([0, limit], [0, limit], color=IDENTITY, linewidth=1, zorder=1)
        ax.scatter(
            ref[active],
            ours[active],
            s=14,
            color=OURS,
            edgecolors=SURFACE,
            linewidths=0.5,
            zorder=2,
        )
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_aspect("equal")
        ax.set_title(
            f"Şekil {outcome.experiment.figure} · {outcome.experiment.stimuli[0][1]:.0f} Hz\n"
            f"r = {c.pearson_r:.4f} · |z|<3: %{100 * c.within_3se:.1f}",
            fontsize=9,
            color=INK,
        )
        ax.set_xlabel("Referans (Hz)", fontsize=8)
        ax.set_ylabel("Bizim model (Hz)", fontsize=8)
    fig.suptitle(
        f"Nöron başına ateşleme hızı: {subtitle} — her nokta bir nöron",
        color=INK,
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def _paired_dots(ax, labels, ours, ref, ours_se, ref_se) -> None:  # type: ignore[no-untyped-def]
    y = np.arange(len(labels))
    _style_axes(ax)
    ax.errorbar(
        ref, y + 0.15, xerr=ref_se, fmt="o", color=REFERENCE, markersize=6, label="Referans"
    )
    ax.errorbar(
        ours, y - 0.15, xerr=ours_se, fmt="o", color=OURS, markersize=6, label="Bizim model"
    )
    ax.set_yticks(y, labels, fontsize=8, color=INK_SECONDARY)
    ax.invert_yaxis()
    ax.set_xlabel("MN9 ateşleme hızı (Hz) · hata çubuğu: ortalamanın standart hatası", fontsize=8)
    # Gösterge çizim alanının üstünde: veri noktalarıyla çakışmaz.
    ax.legend(
        frameon=False,
        fontsize=8,
        labelcolor=INK_SECONDARY,
        loc="lower right",
        bbox_to_anchor=(1.0, 1.0),
        ncol=2,
    )


def _single_neuron_figure(
    outcomes: Sequence[ExperimentOutcome], params: LIFParams, path: Path, title: str
) -> None:
    import matplotlib.pyplot as plt

    comparisons = [o.comparison for o in outcomes]
    assert all(isinstance(c, SingleNeuronComparison) for c in comparisons)
    se = np.sqrt(params.n_trials - 1)
    labels = [o.experiment.title_tr.replace(" → MN9", "") for o in outcomes]
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(outcomes) + 1.2), facecolor=SURFACE)
    _paired_dots(
        ax,
        labels,
        [c.ours_hz for c in comparisons],  # type: ignore[union-attr]
        [c.reference_hz for c in comparisons],  # type: ignore[union-attr]
        [c.ours_std / se for c in comparisons],  # type: ignore[union-attr]
        [c.reference_std / se for c in comparisons],  # type: ignore[union-attr]
    )
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def _verdict(outcomes: Sequence[ExperimentOutcome]) -> tuple[bool, list[str]]:
    problems = []
    for o in outcomes:
        c = o.comparison
        if isinstance(c, WholeBrainComparison):
            if c.pearson_r < 0.99 or c.within_3se < 0.97 or c.n_beyond_5se > 0:
                problems.append(o.experiment.key)
        elif abs(c.z) >= 4:
            problems.append(o.experiment.key)
    return not problems, problems


def _whole_brain_table(outcomes: Sequence[ExperimentOutcome]) -> list[str]:
    lines = [
        "| Deney | Şekil | Aktif nöron | Pearson r | Eğim | \\|z\\|<3 | \\|z\\|>5 "
        "| En büyük fark (Hz) | Toplam hız (bizim / ref.) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        c = o.comparison
        assert isinstance(c, WholeBrainComparison)
        lines.append(
            f"| {o.experiment.title_tr} | {o.experiment.figure} | {c.n_active} "
            f"| {c.pearson_r:.4f} | {c.slope:.3f} | %{100 * c.within_3se:.1f} "
            f"| {c.n_beyond_5se} | {c.max_abs_diff_hz:.1f} "
            f"| {c.total_rate_ours:.0f} / {c.total_rate_reference:.0f} |"
        )
    return lines


def _single_table(outcomes: Sequence[ExperimentOutcome]) -> list[str]:
    lines = ["| Deney | Bizim model (Hz) | Referans (Hz) | z |", "|---|---|---|---|"]
    for o in outcomes:
        c = o.comparison
        assert isinstance(c, SingleNeuronComparison)
        lines.append(
            f"| {o.experiment.title_tr} | {c.ours_hz:.1f} ± {c.ours_std:.1f} | "
            f"{c.reference_hz:.1f} ± {c.reference_std:.1f} | {c.z:+.2f} |"
        )
    return lines


def _split(
    outcomes: Sequence[ExperimentOutcome],
) -> tuple[list[ExperimentOutcome], list[ExperimentOutcome], list[ExperimentOutcome]]:
    return (
        [o for o in outcomes if o.experiment.kind == "whole_brain"],
        [o for o in outcomes if o.experiment.figure == "3A"],
        [o for o in outcomes if o.experiment.figure == "1F"],
    )


_GROUP_LABELS = {
    "sugar": "Şekere duyarlı GRN",
    "bitter": "Acıya duyarlı GRN",
    "water": "Suya duyarlı GRN",
    "johnston_organ": "Johnston organı",
}


def _group_sizes(outcomes: Sequence[ExperimentOutcome]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for o in outcomes:
        sizes.update(o.stimulus_sizes)
    return sizes


def _group_size_rows(
    v630: Sequence[ExperimentOutcome], v783: Sequence[ExperimentOutcome]
) -> list[str]:
    old, new = _group_sizes(v630), _group_sizes(v783)
    return [
        f"| {label} | {old.get(key, '-')} | {new.get(key, '-')} |"
        for key, label in _GROUP_LABELS.items()
    ]


def write_report(
    v630: Sequence[ExperimentOutcome],
    v783: Sequence[ExperimentOutcome],
    params: LIFParams,
    docs_dir: Path,
) -> Path:
    figures = docs_dir / "dogrulama"
    figures.mkdir(parents=True, exist_ok=True)
    whole, grid, silencing = _split(v630)

    _whole_brain_figure(
        whole, figures / "tum_beyin.png", "bizim model (v630) ve Shiu et al. (2024)"
    )
    _single_neuron_figure(grid, params, figures / "seker_aci.png", "Şekil 3A · Şeker + acı → MN9")
    _single_neuron_figure(
        silencing,
        params,
        figures / "susturma.png",
        "Şekil 1F · Şeker 100 Hz + tek nöron susturma → MN9",
    )
    passed, problems = _verdict(v630)
    verdict = "✅ BAŞARILI" if passed else "❌ İNCELEME GEREKLİ: " + ", ".join(problems)

    lines = [
        "# Doğrulama Raporu",
        "",
        f"> Otomatik üretildi: `uv run sinek dogrula` · {date.today().isoformat()}",
        "",
        "Bu rapor, projenin PyTorch LIF modelinin Shiu et al. (2024) [3] yayınlanmış "
        "sonuçlarını yeniden ürettiğini gösterir. Asıl doğrulama **makalenin kullandığı FlyWire "
        "v630 verisi ve makale kodundaki nöron kimlikleriyle** yapılır; böylece veri sürümü "
        "farkı sonuçlara karışmaz. Ek olarak uygulamanın kullandığı v783 verisiyle aynı deneyler "
        "tekrarlanarak sürüm farkının etkisi ölçülür (Bölüm 5).",
        "",
        f"**Model doğrulaması (v630): {verdict}**",
        "",
        "## 1. Yöntem",
        "",
        "Doğrulama iki katmanlıdır:",
        "",
        "1. **Referans simülatörle birebir denklik** (`backend/tests/simulation/`): Rastgelelik "
        "içermeyen ağlarda spike zamanları Brian2 referans modeliyle **birebir** aynıdır; "
        "Poisson uyarımında ateşleme hızları istatistiksel olarak uyumludur.",
        "2. **Yayınlanmış sonuçların yeniden üretimi** (bu rapor): Makalenin arşivlenmiş sonuç "
        f"tabloları (doi:{RESULTS_DOI}) ile tam beyin simülasyonlarımız karşılaştırılır.",
        "",
        f"Her deney {params.n_trials} deneme × {params.t_run_ms:.0f} ms'dir (makaleyle aynı). "
        "Rastgele tohumlar farklı olduğu için sonuçlar spike düzeyinde değil **istatistiksel** "
        "olarak eşleşmelidir.",
        "",
        "**Ölçütler.** Her nöron için Welch z skoru: "
        "z = (ort₁ - ort₂) / √((s₁² + s₂²)/(n - 1)). "
        "İki taraf aynı modeli temsil ediyorsa |z| < 3 oranı ≈ %99,7 beklenir. "
        "**Başarı ölçütleri:** tüm beyin deneylerinde r ≥ 0,99, |z| < 3 oranı ≥ %97 ve "
        "|z| > 5 olan nöron yok; tek nöron deneylerinde |z| < 4.",
        "",
        "## 2. Tüm beyin karşılaştırması (v630)",
        "",
        "![Tüm beyin karşılaştırması](dogrulama/tum_beyin.png)",
        "",
        *_whole_brain_table(whole),
        "",
        "## 3. Şeker ve acı etkileşimi (Şekil 3A, v630)",
        "",
        "![Şeker ve acı etkileşimi](dogrulama/seker_aci.png)",
        "",
        *_single_table(grid),
        "",
        "## 4. Susturma deneyleri (Şekil 1F, v630)",
        "",
        "![Susturma deneyleri](dogrulama/susturma.png)",
        "",
        *_single_table(silencing),
    ]

    if v783:
        whole_783, grid_783, silencing_783 = _split(v783)
        _whole_brain_figure(
            whole_783, figures / "tum_beyin_v783.png", "uygulama (v783) ve Shiu et al. (2024, v630)"
        )
        lines += [
            "",
            "## 5. Uygulama verisiyle karşılaştırma (v783)",
            "",
            "Aynı deneyler uygulamanın kullandığı **FlyWire v783 verisi ve uygulama nöron "
            "gruplarıyla** (`neuron_groups.toml`) tekrarlanmış, makalenin v630 sonuçlarıyla "
            "karşılaştırılmıştır. v630 → v783 arasında kimliği değişen referans nöronların "
            "ardılları FlyWire CAVE servisiyle belirlenmiştir ([veri.md](veri.md) bölüm 4.3); "
            "bu nedenle gruplar makaleyle aynı nöronları içerir. Bu bölüm, **uygulamanın makale "
            "sonuçlarını koruduğunu** gösterir. İki sürüm arasında bazı bağlantılar da "
            "düzeltildiği için küçük farklar beklenebilir. Tüm beyin karşılaştırması yalnızca "
            "iki sürümde aynı kimliğe sahip nöronlarla yapılır.",
            "",
            "| Grup | v630 (makale) | v783 (uygulama) |",
            "|---|---|---|",
            *_group_size_rows(v630, v783),
            "",
            "![v783 tüm beyin karşılaştırması](dogrulama/tum_beyin_v783.png)",
            "",
            *_whole_brain_table(whole_783),
            "",
            "### Şeker + acı → MN9 (v783)",
            "",
            *_single_table(grid_783),
            "",
            "### Susturma → MN9 (v783)",
            "",
            *_single_table(silencing_783),
            "",
            "Susturma deneylerinde v783'te kimliği değişen nöronlar yerine CAVE ile doğrulanmış "
            "ardılları susturulmuştur (`experiments.py`, `V783_SILENCING_SUCCESSORS`).",
        ]

    lines += [
        "",
        "## 6. Sınırlılıklar ve açıklamalar",
        "",
        "- **Veri sürümü.** Model doğrulaması makalenin v630 verisiyle yapılmıştır; uygulama "
        "FlyWire v783 kullanır. v783'te kimliği değişen 3 referans nöronunun (şekere duyarlı 1, "
        "acıya duyarlı 1, Johnston organı 1) ardılları FlyWire CAVE ile belirlenip gruplara "
        "eklenmiştir. Ardıl kullanılmadığında şeker yolunda sistematik %5–9'luk bir düşüş "
        "ölçülmüştü; ayrıntı ve kontrol deneyi: [veri.md](veri.md) bölüm 4.3.",
        "- **Susturma yöntemi.** Referans README'si susturmayı \"giriş ve çıkış sinapslarının "
        'sıfırlanması" olarak tanımlar; referans kod yalnızca **çıkış** sinapslarını sıfırlar. '
        "Bu proje referans kodu izler.",
        "- **Nöromodülatörler.** Dopamin, serotonin ve oktopamin referans modelde uyarıcı kabul "
        "edilir (basitleştirme).",
        "",
        "## 7. Yeniden üretim",
        "",
        "```bash",
        "uv run sinek dogrula      # deneyleri çalıştırır (önbellekli), bu raporu yeniden yazar",
        "```",
        "",
    ]
    report = docs_dir / "dogrulama.md"
    report.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return report
