"""Laboratuvar nöron seçimi: uyarılacak ya da susturulacak nöronların belirlenmesi.

Seçiciler (`NeuronSelector`) kullanıcı girdisini model indekslerine çevirir. Her seçim, raporda
saklanabilmesi ve başka bir bilgisayarda birebir tekrarlanabilmesi için **çözümlenmiş kimliklerle**
birlikte döndürülür.

Seçim türleri:
    group             `neuron_groups.toml` içindeki hazır grup (ör. sugar, mn9)
    cell_type         FlyWire hücre tipi (ör. LB3, DNp01) — anotasyonlardan
    neurotransmitter  nörotransmitter tahmini (ör. gaba) — anotasyonlardan
    neuropil          çıkış sinapslarının çoğunluğu bu nöropilde olan nöronlar
    ids               tek tek FlyWire kimlikleri
"""

from typing import Annotated, Any, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
)

from sinek.connectome.connectome import (
    EXCITATORY_TRANSMITTERS,
    INHIBITORY_TRANSMITTERS,
)
from sinek.connectome.pipeline import IndexBundle

MAX_IDS = 500


def _to_int(value: Any) -> Any:
    """FlyWire kimlikleri 2^53'ten büyüktür; JavaScript tam tutamadığı için metin taşınır."""
    if isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise ValueError(f"Geçersiz FlyWire kimliği: {value}")
        return int(text)
    return value


FlywireId = Annotated[
    int,
    BeforeValidator(_to_int),
    PlainSerializer(str, return_type=str),
    WithJsonSchema({"type": "string", "pattern": "^[0-9]{1,20}$"}, mode="validation"),
]
TRANSMITTERS = tuple(sorted(EXCITATORY_TRANSMITTERS | INHIBITORY_TRANSMITTERS))


class SelectionError(ValueError):
    """Seçim hiçbir nörona karşılık gelmiyor ya da geçersiz."""


class _Selector(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GroupSelector(_Selector):
    kind: Literal["group"] = "group"
    group: str


class CellTypeSelector(_Selector):
    kind: Literal["cell_type"] = "cell_type"
    cell_type: str = Field(min_length=1, max_length=100)


class TransmitterSelector(_Selector):
    kind: Literal["neurotransmitter"] = "neurotransmitter"
    neurotransmitter: str = Field(min_length=3, max_length=20)


class NeuropilSelector(_Selector):
    kind: Literal["neuropil"] = "neuropil"
    neuropil: str = Field(min_length=2, max_length=20)


class IdsSelector(_Selector):
    kind: Literal["ids"] = "ids"
    ids: tuple[FlywireId, ...] = Field(min_length=1, max_length=MAX_IDS)


NeuronSelector = Annotated[
    GroupSelector | CellTypeSelector | TransmitterSelector | NeuropilSelector | IdsSelector,
    Field(discriminator="kind"),
]


class Selection(BaseModel):
    """Çözümlenmiş seçim: kullanıcıya gösterilen tanım + tekrar üretilebilir kimlik listesi."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    selector: NeuronSelector
    label_tr: str
    flywire_ids: tuple[FlywireId, ...]
    missing_ids: tuple[FlywireId, ...] = ()

    @property
    def size(self) -> int:
        return len(self.flywire_ids)


def _dominant_neuropil(bundle: IndexBundle) -> pd.Series:
    """Her nöronun çıkış sinapslarının en yoğun olduğu nöropil (model indeksine göre)."""
    if bundle.neuropils is None:
        raise SelectionError("Nöropil verisi yüklenmemiş")
    counts = bundle.neuropils.counts
    dominant = np.asarray(counts.argmax(axis=1)).ravel()
    totals = np.asarray(counts.sum(axis=1)).ravel()
    names = np.array(bundle.neuropils.names)
    labels = np.where(totals > 0, names[dominant], "")
    return pd.Series(labels, name="neuropil")


def resolve_selector(selector: NeuronSelector, bundle: IndexBundle) -> Selection:
    """Seçiciyi FlyWire kimliklerine çevirir. Boş sonuç hata sayılır (sessiz boş deney olmaz)."""
    annotations = bundle.annotations
    match selector:
        case GroupSelector(group=group):
            resolved = bundle.groups.get(group)
            if resolved is None:
                raise SelectionError(f"Bilinmeyen nöron grubu: {group}")
            label = resolved.definition.name_tr
            ids = resolved.flywire_ids
            missing: tuple[int, ...] = resolved.missing_ids
        case CellTypeSelector(cell_type=cell_type):
            mask = annotations["cell_type"] == cell_type
            label = f"{cell_type} hücre tipi"
            ids = tuple(int(i) for i in annotations.index[mask])
            missing = ()
        case TransmitterSelector(neurotransmitter=transmitter):
            name = transmitter.strip().lower()
            if name not in TRANSMITTERS:
                raise SelectionError(
                    f"Bilinmeyen nörotransmitter: {transmitter} ({', '.join(TRANSMITTERS)})"
                )
            mask = annotations["top_nt"].str.lower() == name
            label = f"{name} nöronları"
            ids = tuple(int(i) for i in annotations.index[mask])
            missing = ()
        case NeuropilSelector(neuropil=neuropil):
            dominant = _dominant_neuropil(bundle)
            indices = np.flatnonzero((dominant == neuropil).to_numpy())
            if indices.size == 0:
                raise SelectionError(f"Bilinmeyen nöropil: {neuropil}")
            label = f"{neuropil} bölgesi"
            ids = tuple(int(i) for i in bundle.neurons.flywire_ids[indices])
            missing = ()
        case IdsSelector(ids=requested):
            _, absent = bundle.neurons.index_of(list(requested))
            label = f"{len(requested)} nöron kimliği"
            ids = tuple(i for i in requested if i not in set(absent))
            missing = tuple(absent)
        case _:  # pragma: no cover - pydantic ayrıştırıcısı bunu engeller
            raise SelectionError("Bilinmeyen seçim türü")

    present, _ = bundle.neurons.index_of(list(ids))
    if present.size == 0:
        raise SelectionError(f"Seçim modelde hiçbir nörona karşılık gelmiyor: {label}")
    return Selection(
        selector=selector,
        label_tr=label,
        flywire_ids=tuple(int(i) for i in bundle.neurons.flywire_ids[np.sort(present)]),
        missing_ids=missing,
    )


def indices_of(selection: Selection, bundle: IndexBundle) -> NDArray[np.int64]:
    indices, _ = bundle.neurons.index_of(list(selection.flywire_ids))
    return np.sort(indices)


def search_cell_types(bundle: IndexBundle, query: str, limit: int = 20) -> list[dict[str, object]]:
    """Hücre tipi arama: önce baştan eşleşenler, sonra içinde geçenler.

    Büyük/küçük harf duyarsızdır. Sayımlar yalnızca **modeldeki** nöronları kapsar: anotasyon
    dosyasında bulunup modele girmeyen nöronlar (tamamlanmamış rekonstrüksiyonlar) sayılmaz.
    """
    text = query.strip().lower()
    if not text:
        raise SelectionError("Arama metni boş olamaz")
    annotations = bundle.annotations
    in_model = np.isin(annotations.index.to_numpy(), bundle.neurons.flywire_ids)
    types = annotations.loc[in_model, "cell_type"].dropna()
    counts = types.value_counts()
    lowered = counts.index.str.lower()
    starts = counts[lowered.str.startswith(text)]
    contains = counts[lowered.str.contains(text, regex=False) & ~lowered.str.startswith(text)]
    ordered = pd.concat([starts, contains]).head(limit)
    return [{"cell_type": str(name), "neuron_count": int(value)} for name, value in ordered.items()]
