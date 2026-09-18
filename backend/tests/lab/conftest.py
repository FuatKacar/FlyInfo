"""Laboratuvar testleri için küçük yapay devre (gerçek veri ve ekran kartı gerekmez).

Dört nöron, güçlü bağlantılar (uyarım gerçekten aşağı akar):
    0 (1000) → 1 (1001)  uyarıcı,  300 sinaps   uyarım kaynağı → beslenme okuması
    1 (1001) → 2 (1002)  baskılayıcı, 200 sinaps   beslenme → kaçış okumasını baskılar
    0 (1000) → 3 (1003)  uyarıcı,  120 sinaps
    3 (1003) → 1 (1001)  baskılayıcı, 150 sinaps   ara nöron beslenmeyi frenler
"""

from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp
import torch

from sinek.connectome.connectome import Connectome, NeuronIndex, build_connectome, load_annotations
from sinek.connectome.groups import Behavior, GroupDefinition, resolve_groups
from sinek.connectome.neuropils import NeuropilMap
from sinek.connectome.pipeline import IndexBundle
from sinek.decoder.decoder import BehaviorCalibration

CPU = torch.device("cpu")
READOUT_IDS = {
    Behavior.FEEDING: 1001,
    Behavior.ESCAPE: 1002,
    Behavior.ANTENNAL_GROOMING: 1003,
    Behavior.BACKWARD_WALKING: 1003,
    Behavior.FORWARD_WALKING: 1003,
}


def definition(key: str, role: str, ids: list[int], **extra: object) -> GroupDefinition:
    return GroupDefinition.model_validate(
        {
            "key": key,
            "role": role,
            "name_tr": f"{key} grubu",
            "description_tr": f"{key} açıklaması",
            "citations": [3],
            "selection": "reference_ids",
            "reference": "test",
            "ids": ids,
            **extra,
        }
    )


IDS = [1000, 1001, 1002, 1003]
# (pre, post, sinaps sayısı, işaret)
EDGES = [(0, 1, 300, 1), (1, 2, 200, -1), (0, 3, 120, 1), (3, 1, 150, -1)]


@pytest.fixture
def lab_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    import pandas as pd

    completeness = tmp_path / "completeness.csv"
    pd.DataFrame({"Completed": [True] * len(IDS)}, index=pd.Index(IDS, name="")).to_csv(
        completeness
    )

    connectivity = tmp_path / "connectivity.parquet"
    pd.DataFrame(
        {
            "Presynaptic_ID": [IDS[p] for p, *_ in EDGES],
            "Postsynaptic_ID": [IDS[q] for _, q, *_ in EDGES],
            "Presynaptic_Index": [p for p, *_ in EDGES],
            "Postsynaptic_Index": [q for _, q, *_ in EDGES],
            "Connectivity": [n for *_, n, _ in EDGES],
            "Excitatory": [s for *_, s in EDGES],
            "Excitatory x Connectivity": [n * s for *_, n, s in EDGES],
        }
    ).to_parquet(connectivity)

    annotations = tmp_path / "annotations.tsv"
    pd.DataFrame(
        {
            "root_id": [*IDS, 9999],  # 9999: modelde olmayan nöron
            "super_class": ["central"] * 5,
            "cell_class": [None] * 5,
            "cell_sub_class": [None] * 5,
            "cell_type": ["A", "B", "B", "C", "B"],
            "hemibrain_type": [None] * 5,
            "side": ["left", "left", "right", "right", "left"],
            "top_nt": ["acetylcholine", "gaba", "glutamate", "acetylcholine", "gaba"],
            "top_nt_conf": [0.9] * 5,
        }
    ).to_csv(annotations, sep="	", index=False)

    return completeness, connectivity, annotations


@pytest.fixture
def connectome(lab_files: tuple[Path, Path, Path]) -> Connectome:
    completeness, connectivity, _ = lab_files
    return build_connectome(completeness, connectivity)


@pytest.fixture
def bundle(lab_files: tuple[Path, Path, Path], connectome: Connectome) -> IndexBundle:
    _, _, annotations_path = lab_files
    annotations = load_annotations(annotations_path)
    definitions = {"uyarici": definition("uyarici", "stimulus", [1000])}
    for behavior, root_id in READOUT_IDS.items():
        definitions[behavior.value] = definition(
            behavior.value, "readout", [root_id], behavior=behavior.value
        )
    neurons = NeuronIndex(connectome.flywire_ids)
    neuropils = NeuropilMap(
        names=("GNG", "PRW"),
        counts=sp.coo_array(
            ([10.0, 4.0, 6.0], ([0, 1, 2], [0, 0, 1])), shape=(connectome.n_neurons, 2)
        ).tocsr(),
    )
    return IndexBundle(
        neurons, annotations, resolve_groups(definitions, neurons, annotations), neuropils
    )


@pytest.fixture
def calibration() -> dict[Behavior, BehaviorCalibration]:
    return {b: BehaviorCalibration(100.0, "test", "test") for b in Behavior}


@pytest.fixture
def rates(connectome: Connectome) -> np.ndarray:
    """Yol analizi için örnek hızlar: tüm nöronlar aktif."""
    return np.array([40.0, 30.0, 20.0, 10.0])[: connectome.n_neurons]


@pytest.fixture
def lab_service(
    bundle: IndexBundle,
    connectome: Connectome,
    calibration: dict[Behavior, BehaviorCalibration],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):  # type: ignore[no-untyped-def]
    """Tam konektom yüklemeden çalışan Laboratuvar servisi (yapay devre, işlemci)."""
    from sinek.connectome.pipeline import DataBundle
    from sinek.lab.service import LabService

    service = LabService(bundle, tmp_path, tmp_path, calibration, device=CPU)
    data = DataBundle(connectome, bundle.annotations, bundle.groups, bundle.neuropils)
    monkeypatch.setattr(service, "_full_bundle", lambda: data)
    return service
