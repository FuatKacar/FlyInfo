"""Beyin şeması geometrisinin üretimi: 3B nöropil ağları → önden görünümlü 2B SVG yolları.

Yöntem:
    1. Ağ köşeleri önden izdüşürülür: ekran_x = -x, ekran_y = y (µm). FlyWire uzayında x sineğin
       sağına, y aşağıya (ventral), z arkaya (posterior) doğru artar; önden bakan izleyici için
       sineğin sağı ekranın solunda görünür.
    2. İzdüşen üçgenler RESOLUTION_UM çözünürlüklü bir maskeye çizilir; maskenin birleşimi ağın
       önden siluetidir (kapalı yüzeyin izdüşümü, yüzey üçgenlerinin izdüşümlerinin birleşimidir).
    3. Maske hafifçe yumuşatılıp 0,5 eş-değer çizgileri çıkarılır (delikler ayrı halka olarak
       korunur, SVG'de `fill-rule="evenodd"` ile çizilir) ve Douglas–Peucker ile sadeleştirilir.
    4. Çizim sırası derinliğe göredir: arkadaki (z ortalaması büyük) bölgeler önce çizilir.

Okuma nöronları şemada hücre gövdesi (soma) konumlarıyla işaretlenir (FlyWire anotasyonları,
voksel boyutu 4 × 4 × 40 nm). Soma konumu yoksa nöronun temsili noktası (pos_*) kullanılır.

Çalıştırma (bakımcı aracı; matplotlib bağımlılıkları gerekir):
    uv run python -m sinek.schematic.build
"""

import hashlib
import json
import struct
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter

from sinek.connectome.groups import GroupRole
from sinek.connectome.pipeline import load_index_bundle, raw_dir
from sinek.connectome.sources import ANNOTATIONS
from sinek.schematic.sources import (
    BRAIN_MESH,
    BRAIN_PREFIX,
    MESH_BASE_URL,
    NEUROPIL_MESHES,
    NEUROPIL_PREFIX,
)

RESOLUTION_UM = 0.5
SMOOTHING_PX = 1.0
SIMPLIFY_UM = 0.6
MIN_RING_AREA_UM2 = 20.0
MARGIN_UM = 8.0
VOXEL_NM = (4.0, 4.0, 40.0)
SCHEMA_VERSION = 1

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = ROOT / "frontend" / "src" / "assets" / "beyin-semasi.json"


class MeshError(ValueError):
    """Ağ dosyası beklenen biçimde değil veya özeti uyuşmuyor."""


# --- Ağ okuma ---------------------------------------------------------------------------------


def parse_fragment(data: bytes) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Neuroglancer 'legacy' ağ parçası: uint32 köşe sayısı, float32 köşeler, uint32 üçgenler."""
    if len(data) < 4:
        raise MeshError("Parça çok kısa")
    (n_vertices,) = struct.unpack("<I", data[:4])
    vertex_bytes = 12 * n_vertices
    face_bytes = len(data) - 4 - vertex_bytes
    if face_bytes < 0 or face_bytes % 12:
        raise MeshError("Parça boyutu köşe sayısıyla uyuşmuyor")
    vertices = np.frombuffer(data, "<f4", 3 * n_vertices, 4).reshape(-1, 3).astype(np.float64)
    faces = np.frombuffer(data, "<u4", offset=4 + vertex_bytes).reshape(-1, 3).astype(np.int64)
    if faces.size and faces.max() >= n_vertices:
        raise MeshError("Üçgen dizini köşe sayısını aşıyor")
    return vertices, faces


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data: bytes = response.read()
    return data


def fetch_mesh(
    cache_dir: Path, prefix: str, segment: int, sha256: str
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Bölümün tüm parçalarını indirir (önbellekli), özetini doğrular ve birleştirir."""
    cache = cache_dir / prefix.replace("/", "__")
    cache.mkdir(parents=True, exist_ok=True)

    def cached(name: str) -> bytes:
        path = cache / name.replace(":", "_")
        if not path.is_file():
            path.write_bytes(_download(f"{MESH_BASE_URL}{prefix}/mesh/{name}"))
        return path.read_bytes()

    fragments = json.loads(cached(f"{segment}:0"))["fragments"]
    digest = hashlib.sha256()
    vertices, faces, offset = [], [], 0
    for fragment in fragments:
        data = cached(fragment)
        digest.update(data)
        v, f = parse_fragment(data)
        vertices.append(v)
        faces.append(f + offset)
        offset += len(v)
    if digest.hexdigest() != sha256:
        raise MeshError(f"{prefix} bölüm {segment}: SHA-256 uyuşmuyor (kaynak değişmiş olabilir)")
    return np.vstack(vertices), np.vstack(faces)


# --- Geometri --------------------------------------------------------------------------------


def front_view(vertices_nm: NDArray[np.float64]) -> NDArray[np.float64]:
    """nm → önden görünüm µm: (-x, y)."""
    return np.column_stack([-vertices_nm[:, 0], vertices_nm[:, 1]]) / 1000.0


def silhouette(
    points: NDArray[np.float64],
    faces: NDArray[np.int64],
    origin: tuple[float, float],
    size: tuple[float, float],
    resolution: float = RESOLUTION_UM,
) -> list[NDArray[np.float64]]:
    """İzdüşen üçgenlerin birleşiminin sınır halkaları (µm, kapalı, ilk nokta = son nokta)."""
    from contourpy import LineType, contour_generator
    from PIL import Image, ImageDraw

    width, height = (int(np.ceil(s / resolution)) + 3 for s in size)
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    pixels = (points - np.asarray(origin)) / resolution + 1.0
    for triangle in pixels[faces]:
        draw.polygon([tuple(p) for p in triangle], fill=255, outline=255)
    mask = np.asarray(image, dtype=np.float64) / 255.0
    if SMOOTHING_PX > 0:
        mask = gaussian_filter(mask, SMOOTHING_PX)

    lines = contour_generator(z=mask, line_type=LineType.Separate).lines(0.5)
    rings = []
    for line in lines:
        ring = np.asarray(line, dtype=np.float64)
        ring = (ring - 1.0) * resolution + np.asarray(origin)
        if abs(ring_area(ring)) >= MIN_RING_AREA_UM2:
            rings.append(ring)
    return rings


def ring_area(ring: NDArray[np.float64]) -> float:
    x, y = ring[:, 0], ring[:, 1]
    return float(0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def simplify(points: NDArray[np.float64], tolerance: float) -> NDArray[np.float64]:
    """Douglas–Peucker; uç noktalar korunur."""
    if len(points) < 3:
        return points
    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        a, b = points[start], points[end]
        segment = b - a
        length = float(np.hypot(*segment))
        middle = points[start + 1 : end]
        if length == 0.0:
            distances = np.hypot(*(middle - a).T)
        else:
            rel = middle - a
            distances = np.abs(segment[0] * rel[:, 1] - segment[1] * rel[:, 0]) / length
        index = int(np.argmax(distances))
        if distances[index] > tolerance:
            split = start + 1 + index
            keep[split] = True
            stack.extend([(start, split), (split, end)])
    return points[keep]


def path_data(rings: list[NDArray[np.float64]], offset: NDArray[np.float64]) -> str:
    parts = []
    for ring in rings:
        simple = simplify(ring, SIMPLIFY_UM)
        if len(simple) < 4:
            continue
        coords = np.round(simple[:-1] - offset, 1)
        body = " ".join(f"{x:g} {y:g}" for x, y in coords)
        parts.append(f"M{body}Z")
    return "".join(parts)


# --- Okuma nöronları --------------------------------------------------------------------------


def readout_markers(data_dir: Path) -> list[dict[str, Any]]:
    bundle = load_index_bundle(data_dir)
    positions = pd.read_csv(
        raw_dir(data_dir) / ANNOTATIONS.filename,
        sep="\t",
        usecols=["root_id", "soma_x", "soma_y", "soma_z", "pos_x", "pos_y", "pos_z", "side"],
        dtype={"root_id": np.int64},
        low_memory=False,
    ).set_index("root_id")
    markers = []
    for key, group in bundle.groups.items():
        d = group.definition
        if d.role is not GroupRole.READOUT or d.behavior is None:
            continue
        neurons = []
        for root_id in group.flywire_ids:
            row = positions.loc[root_id]
            has_soma = bool(pd.notna(row["soma_x"]))
            voxel = (
                row[["soma_x", "soma_y", "soma_z"]]
                if has_soma
                else row[["pos_x", "pos_y", "pos_z"]]
            )
            nm = voxel.to_numpy(dtype=np.float64) * np.asarray(VOXEL_NM)
            (x, y) = front_view(nm[None, :])[0]
            neurons.append(
                {
                    "root_id": str(root_id),
                    "side": None if pd.isna(row["side"]) else str(row["side"]),
                    "point": [float(x), float(y)],
                    "position": "soma" if has_soma else "temsili",
                }
            )
        markers.append({"group": key, "behavior": d.behavior.value, "neurons": neurons})
    return markers


# --- Üretim ----------------------------------------------------------------------------------


def build(data_dir: Path, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    cache_dir = raw_dir(data_dir) / "neuropil_meshes"
    brain_v, brain_f = fetch_mesh(cache_dir, BRAIN_PREFIX, *BRAIN_MESH)
    meshes = {
        name: fetch_mesh(cache_dir, NEUROPIL_PREFIX, segment, sha)
        for name, (segment, sha) in NEUROPIL_MESHES.items()
    }

    all_points = np.vstack([front_view(brain_v), *(front_view(v) for v, _ in meshes.values())])
    low = all_points.min(axis=0) - MARGIN_UM
    high = all_points.max(axis=0) + MARGIN_UM
    origin, size = (
        (float(low[0]), float(low[1])),
        (float(high[0] - low[0]), float(high[1] - low[1])),
    )

    def shape(v: NDArray[np.float64], f: NDArray[np.int64]) -> str:
        return path_data(silhouette(front_view(v), f, origin, size), low)

    neuropils: list[dict[str, Any]] = []
    for name, (v, f) in meshes.items():
        center = front_view(v).mean(axis=0) - low
        neuropils.append(
            {
                "name": name,
                "d": shape(v, f),
                "center": [round(float(c), 1) for c in center],
                "depth_um": round(float(v[:, 2].mean() / 1000.0), 1),
            }
        )
    neuropils.sort(key=lambda n: -float(n["depth_um"]))  # arkadan öne

    markers = readout_markers(data_dir)
    for marker in markers:
        for neuron in marker["neurons"]:
            neuron["point"] = [
                round(float(p - o), 1) for p, o in zip(neuron["point"], low, strict=True)
            ]

    schematic: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "view": "anterior",  # önden; sineğin sağı ekranın solunda
        "units": "µm",
        "width": round(size[0], 1),
        "height": round(size[1], 1),
        "outline": shape(brain_v, brain_f),
        "neuropils": neuropils,
        "readouts": markers,
        "source": {
            "meshes": f"{MESH_BASE_URL}{NEUROPIL_PREFIX}",
            "brain_mesh": f"{MESH_BASE_URL}{BRAIN_PREFIX}",
            "annotations": ANNOTATIONS.filename,
            "citations": ["dorkenwald2024", "schlegel2024", "ito2014", "jenett2012"],
            "method": "önden ortografik izdüşüm, silüet, Douglas–Peucker",
            "resolution_um": RESOLUTION_UM,
            "simplify_um": SIMPLIFY_UM,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(schematic, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return schematic


if __name__ == "__main__":
    from sinek.config import get_settings

    result = build(get_settings().data_dir)
    size_kb = DEFAULT_OUTPUT.stat().st_size / 1024
    print(f"{len(result['neuropils'])} nöropil, {size_kb:.0f} KB → {DEFAULT_OUTPUT}")
