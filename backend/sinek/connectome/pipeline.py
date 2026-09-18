"""Veri hazırlama hattı: indir → doğrula → matrisi kur → grupları çözümle → raporla."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from sinek.connectome.connectome import (
    Connectome,
    NeuronIndex,
    SignSource,
    build_connectome,
    load_annotations,
    load_neuron_index,
)
from sinek.connectome.download import ProgressCallback, download_all
from sinek.connectome.groups import ResolvedGroup, load_group_definitions, resolve_groups
from sinek.connectome.neuropils import NeuropilMap, load_neuropil_map
from sinek.connectome.sources import (
    ANNOTATIONS,
    COMPLETENESS,
    CONNECTIVITY,
    NEUROPIL_PRE_COUNTS,
)


@dataclass(frozen=True)
class DataBundle:
    connectome: Connectome
    annotations: pd.DataFrame
    groups: dict[str, ResolvedGroup]
    neuropils: NeuropilMap | None = None


def raw_dir(data_dir: Path) -> Path:
    return data_dir / "raw"


def load_bundle(data_dir: Path, sign_source: SignSource = SignSource.REFERENCE) -> DataBundle:
    """İndirilmiş ham veriden konektomu ve nöron gruplarını yükler."""
    raw = raw_dir(data_dir)
    annotations = load_annotations(raw / ANNOTATIONS.filename)
    connectome = build_connectome(
        raw / COMPLETENESS.filename,
        raw / CONNECTIVITY.filename,
        sign_source=sign_source,
        annotations=annotations,
    )
    groups = resolve_groups(load_group_definitions(), connectome, annotations)
    neuropil_path = raw / NEUROPIL_PRE_COUNTS.filename
    neuropils = load_neuropil_map(neuropil_path, connectome) if neuropil_path.is_file() else None
    return DataBundle(connectome, annotations, groups, neuropils)


@dataclass(frozen=True)
class IndexBundle:
    """Bağlantı matrisi olmadan yüklenen kaynaklar: hazır senaryoları çözümlemek için yeterlidir.

    Nöron sırası ve grup çözümlemesi `load_bundle` ile birebir aynıdır (aynı dosyalar, aynı kod).
    """

    neurons: NeuronIndex
    annotations: pd.DataFrame
    groups: dict[str, ResolvedGroup]
    neuropils: NeuropilMap | None = None


def load_index_bundle(data_dir: Path) -> IndexBundle:
    raw = raw_dir(data_dir)
    annotations = load_annotations(raw / ANNOTATIONS.filename)
    neurons = load_neuron_index(raw / COMPLETENESS.filename)
    groups = resolve_groups(load_group_definitions(), neurons, annotations)
    neuropil_path = raw / NEUROPIL_PRE_COUNTS.filename
    neuropils = load_neuropil_map(neuropil_path, neurons) if neuropil_path.is_file() else None
    return IndexBundle(neurons, annotations, groups, neuropils)


def prepare(data_dir: Path, progress: ProgressCallback | None = None) -> DataBundle:
    download_all(raw_dir(data_dir), progress=progress)
    return load_bundle(data_dir)


def format_report(bundle: DataBundle) -> str:
    c = bundle.connectome
    lines = [
        "Konektom (FlyWire v783)",
        f"  Nöron sayısı      : {c.n_neurons:>12,}".replace(",", "."),
        f"  Bağlantı sayısı   : {c.n_connections:>12,}".replace(",", "."),
        f"  Sinaps sayısı     : {c.n_synapses:>12,}".replace(",", "."),
        f"  İşaret kaynağı    : {c.sign_source.value}",
        "",
        "Nöron grupları",
    ]
    for key, group in bundle.groups.items():
        d = group.definition
        status = "TAMAM" if group.size else "BOŞ!"
        notes = []
        if group.substituted:
            notes.append(f"{len(group.substituted)} v783 ardılı")
        if group.missing_ids:
            notes.append(f"{len(group.missing_ids)} kayıp kimlik")
        suffix = f", {', '.join(notes)}" if notes else ""
        lines.append(
            f"  [{status:5}] {key:15} {d.role.value:8} {group.size:4} nöron{suffix}  ({d.name_tr})"
        )
    return "\n".join(lines)
