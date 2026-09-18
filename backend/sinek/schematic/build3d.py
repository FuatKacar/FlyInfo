"""Beyin şemasının 3B geometrisi: nöropil ağları → tarayıcıda döndürülebilir model.

2B şemayla (bkz. `build.py`) aynı kaynak ağları kullanır; fark yalnızca izdüşüm yerine üç boyutlu
geometrinin doğrudan aktarılmasıdır.

Görüntüleyici eksenleri (three.js: x sağa, y yukarı, z izleyiciye doğru):
    x =  -x_flywire / 1000      sineğin sağı ekranın solunda (2B şemayla aynı yön)
    y =  -y_flywire / 1000      dorsal (üst) yukarıda
    z =  -z_flywire / 1000      anterior (ön) izleyiciye doğru
Model ağırlık merkezine göre ortalanır; birim mikrometredir.

Çıktı iki dosyadır:
    frontend/public/beyin-3b.bin        int16 köşeler + uint32 üçgen dizinleri (tek blok)
    frontend/src/assets/beyin-3b.json   ölçek, parça tablosu, okuma nöronları, SHA-256

Köşeler int16'ya niceleştirilir: 0,03 µm'den küçük bir yuvarlama hatası (beyin ≈ 850 µm) görsel
olarak fark edilemez, dosya yarı yarıya küçülür.

Çalıştırma: uv run python -m sinek.schematic.build3d
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sinek.schematic.build import ROOT, VOXEL_NM, fetch_mesh, readout_markers
from sinek.schematic.sources import (
    BRAIN_MESH,
    BRAIN_PREFIX,
    MESH_BASE_URL,
    NEUROPIL_MESHES,
    NEUROPIL_PREFIX,
)

SCHEMA_VERSION = 1
INT16_MAX = 32767
DEFAULT_BINARY = ROOT / "frontend" / "public" / "beyin-3b.bin"
DEFAULT_INDEX = ROOT / "frontend" / "src" / "assets" / "beyin-3b.json"


def view_space(vertices_nm: NDArray[np.float64]) -> NDArray[np.float64]:
    """FlyWire nm → görüntüleyici µm (sağ-sol, üst-alt ve ön-arka yönleri düzeltilmiş)."""
    return np.column_stack([-vertices_nm[:, 0], -vertices_nm[:, 1], -vertices_nm[:, 2]]) / 1000.0


def index_mesh(
    vertices: NDArray[np.float64], faces: NDArray[np.int64]
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Yinelenen köşeleri birleştirir (beyin ağı dizinsiz üçgen yığını olarak gelir)."""
    unique, inverse = np.unique(vertices, axis=0, return_inverse=True)
    return unique, inverse[faces].reshape(-1, 3)


def build(
    output_binary: Path = DEFAULT_BINARY, output_index: Path = DEFAULT_INDEX
) -> dict[str, Any]:
    from sinek.config import get_settings

    data_dir = get_settings().data_dir
    cache_dir = data_dir / "raw" / "neuropil_meshes"

    meshes: dict[str, tuple[NDArray[np.float64], NDArray[np.int64]]] = {}
    brain_v, brain_f = index_mesh(*fetch_mesh(cache_dir, BRAIN_PREFIX, *BRAIN_MESH))
    meshes["__beyin__"] = (view_space(brain_v), brain_f)
    for name, (segment, sha) in NEUROPIL_MESHES.items():
        v, f = fetch_mesh(cache_dir, NEUROPIL_PREFIX, segment, sha)
        meshes[name] = (view_space(v), f)

    all_points = np.vstack([v for v, _ in meshes.values()])
    center = (all_points.min(axis=0) + all_points.max(axis=0)) / 2
    radius = float(np.abs(all_points - center).max())
    scale = radius / INT16_MAX  # int16 birimi → µm

    positions: list[NDArray[np.int16]] = []
    indices: list[NDArray[np.uint32]] = []
    parts: list[dict[str, Any]] = []
    vertex_offset = index_offset = 0
    for name, (v, f) in meshes.items():
        quantized = np.rint((v - center) / scale).astype(np.int16)
        positions.append(quantized)
        indices.append(f.astype(np.uint32) + vertex_offset)
        parts.append(
            {
                "name": name,
                "vertex_offset": vertex_offset,
                "vertex_count": len(v),
                "index_offset": index_offset,
                "index_count": int(f.size),
                "depth_um": round(float(v[:, 2].mean()), 1),
            }
        )
        vertex_offset += len(v)
        index_offset += int(f.size)

    vertex_bytes = np.concatenate(positions).tobytes()
    # uint32 dizinlerin 4 baytlık hizaya oturması gerekir (tarayıcıda Uint32Array görünümü).
    padding = bytes(-len(vertex_bytes) % 4)
    index_bytes = np.concatenate(indices).ravel().tobytes()
    payload = vertex_bytes + padding + index_bytes
    output_binary.parent.mkdir(parents=True, exist_ok=True)
    output_binary.write_bytes(payload)

    markers = readout_markers(data_dir)
    for marker in markers:
        for neuron in marker["neurons"]:
            neuron.pop("point", None)
    positions_nm = _readout_positions(data_dir, markers)
    for marker in markers:
        for neuron in marker["neurons"]:
            point = positions_nm[int(neuron["root_id"])] - center
            neuron["point"] = [round(float(c), 1) for c in point]

    index: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "units": "µm",
        "binary": output_binary.name,
        "binary_sha256": hashlib.sha256(payload).hexdigest(),
        "scale": scale,  # int16 birimi → µm
        "radius_um": round(radius, 1),
        "size_um": [round(float(x), 1) for x in (all_points.max(axis=0) - all_points.min(axis=0))],
        "vertex_bytes": len(vertex_bytes),
        "index_byte_offset": len(vertex_bytes) + len(padding),
        "parts": parts,
        "readouts": markers,
        "source": {
            "meshes": f"{MESH_BASE_URL}{NEUROPIL_PREFIX}",
            "brain_mesh": f"{MESH_BASE_URL}{BRAIN_PREFIX}",
            "citations": ["dorkenwald2024", "schlegel2024", "ito2014", "jenett2012"],
            "view": "x: -x_flywire, y: -y_flywire, z: -z_flywire (µm, merkezlenmiş)",
        },
    }
    output_index.parent.mkdir(parents=True, exist_ok=True)
    output_index.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return index


def _readout_positions(
    data_dir: Path, markers: list[dict[str, Any]]
) -> dict[int, NDArray[np.float64]]:
    """Okuma nöronlarının görüntüleyici uzayındaki (µm) konumları."""
    import pandas as pd

    from sinek.connectome.pipeline import raw_dir
    from sinek.connectome.sources import ANNOTATIONS

    ids = [int(n["root_id"]) for m in markers for n in m["neurons"]]
    table = pd.read_csv(
        raw_dir(data_dir) / ANNOTATIONS.filename,
        sep="\t",
        usecols=["root_id", "soma_x", "soma_y", "soma_z", "pos_x", "pos_y", "pos_z"],
        dtype={"root_id": np.int64},
        low_memory=False,
    ).set_index("root_id")
    result = {}
    for root_id in ids:
        row = table.loc[root_id]
        has_soma = bool(pd.notna(row["soma_x"]))
        voxel = (
            row[["soma_x", "soma_y", "soma_z"]] if has_soma else row[["pos_x", "pos_y", "pos_z"]]
        )
        nm = voxel.to_numpy(dtype=np.float64) * np.asarray(VOXEL_NM)
        result[root_id] = view_space(nm[None, :])[0]
    return result


if __name__ == "__main__":
    result = build()
    size_mb = DEFAULT_BINARY.stat().st_size / 1024 / 1024
    print(f"{len(result['parts']) - 1} nöropil + beyin kabuğu, {size_mb:.1f} MB → {DEFAULT_BINARY}")
