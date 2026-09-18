"""Ham veri kaynakları.

Her dosya belirli bir git commit'ine sabitlenmiştir ve SHA-256 özetiyle doğrulanır.
Böylece her makinede bayt bayt aynı veri kullanılır.
"""

from dataclasses import dataclass

SHIU_COMMIT = "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960"
ANNOTATIONS_COMMIT = "8587524c1748ce5ef2080822a2fc890fc03bf597"

_SHIU_RAW = f"https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/{SHIU_COMMIT}"
_ANNOTATIONS_RAW = (
    f"https://raw.githubusercontent.com/flyconnectome/flywire_annotations/{ANNOTATIONS_COMMIT}"
)


@dataclass(frozen=True)
class DataSource:
    key: str
    filename: str
    url: str
    sha256: str
    size: int
    description: str
    license: str
    citations: tuple[int, ...]  # docs/yol-haritasi.md Bölüm 8 numaraları


COMPLETENESS = DataSource(
    key="completeness",
    filename="Completeness_783.csv",
    url=f"{_SHIU_RAW}/Completeness_783.csv",
    sha256="bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311",
    size=3_327_347,
    description="FlyWire v783 modele dahil nöronların listesi (sıra = model indeksi)",
    license="MIT (kod deposu) / CC-BY 4.0 (FlyWire verisi)",
    citations=(1, 3),
)

CONNECTIVITY = DataSource(
    key="connectivity",
    filename="Connectivity_783.parquet",
    url=f"{_SHIU_RAW}/Connectivity_783.parquet",
    sha256="efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347",
    size=100_804_642,
    description="FlyWire v783 işaretli sinaptik bağlantı tablosu",
    license="MIT (kod deposu) / CC-BY 4.0 (FlyWire verisi)",
    citations=(1, 3, 4),
)

ANNOTATIONS = DataSource(
    key="annotations",
    filename="Supplemental_file1_neuron_annotations.tsv",
    url=f"{_ANNOTATIONS_RAW}/supplemental_files/Supplemental_file1_neuron_annotations.tsv",
    sha256="9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be",
    size=31_718_505,
    description="FlyWire v783 nöron anotasyonları (hücre tipi, sınıf, nörotransmitter, taraf)",
    license="CC-BY 4.0",
    citations=(2, 4, 5, 7),
)

NEUROPIL_PRE_COUNTS = DataSource(
    key="neuropil_pre_counts",
    filename="per_neuron_neuropil_count_pre_783.feather",
    url=(
        "https://zenodo.org/records/10676866/files/"
        "per_neuron_neuropil_count_pre_783.feather?download=1"
    ),
    sha256="35442a46f076892dff91bd6e55fa1489b3acc64fda1d35cee7dbbbbc509a3dff",
    size=16_853_770,
    description="FlyWire v783 nöron başına nöropil bazında çıkış (presinaptik) sinaps sayıları",
    license="CC-BY 4.0 (Zenodo 10.5281/zenodo.10676866, sürüm 783.0)",
    citations=(1,),
)

SOURCES: tuple[DataSource, ...] = (COMPLETENESS, CONNECTIVITY, ANNOTATIONS, NEUROPIL_PRE_COUNTS)
