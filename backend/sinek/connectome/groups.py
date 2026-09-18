"""Uyarım ve okuma nöron gruplarının tanımı ve v783 verisinde çözümlenmesi."""

import hashlib
import json
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator

from sinek.connectome.connectome import Connectome, NeuronIndex

DEFAULT_GROUPS_PATH = Path(__file__).with_name("neuron_groups.toml")


class GroupRole(StrEnum):
    STIMULUS = "stimulus"
    READOUT = "readout"


class Behavior(StrEnum):
    FEEDING = "feeding"
    ESCAPE = "escape"
    ANTENNAL_GROOMING = "antennal_grooming"
    BACKWARD_WALKING = "backward_walking"
    FORWARD_WALKING = "forward_walking"


class GroupDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    role: GroupRole
    name_tr: str
    description_tr: str
    citations: tuple[int, ...]
    selection: Literal["reference_ids", "annotation"]
    reference: str | None = None
    behavior: Behavior | None = None
    note_tr: str | None = None
    ids: tuple[int, ...] = ()
    cell_types: tuple[str, ...] = ()
    # v630 referans kimliği → v783 ardılı (FlyWire CAVE ile doğrulanmış kimlik değişimleri)
    successors: dict[int, int] = Field(default_factory=dict)
    successors_source: str | None = None
    # Uyarım grubunun çözümleyicide doğrudan davranış karşılığı yok (yalnızca devre aktivitesi)
    circuit_only: bool = False

    @model_validator(mode="after")
    def _check_selection(self) -> Self:
        if self.selection == "reference_ids" and not (self.ids and self.reference):
            raise ValueError(f"{self.key}: reference_ids seçimi için ids ve reference gerekli")
        if not set(self.successors) <= set(self.ids):
            raise ValueError(f"{self.key}: ardılı tanımlanan kimlik referans listesinde yok")
        if self.successors and not self.successors_source:
            raise ValueError(f"{self.key}: ardıl eşlemesinin kaynağı belirtilmeli")
        if self.selection == "annotation" and not self.cell_types:
            raise ValueError(f"{self.key}: annotation seçimi için cell_types gerekli")
        if len(set(self.ids)) != len(self.ids):
            raise ValueError(f"{self.key}: yinelenen kimlik")
        if not self.citations:
            raise ValueError(f"{self.key}: en az bir kaynak gösterilmeli")
        return self


class GroupFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    dataset: str
    group: tuple[GroupDefinition, ...]

    @model_validator(mode="after")
    def _unique_keys(self) -> Self:
        keys = [g.key for g in self.group]
        if len(set(keys)) != len(keys):
            raise ValueError("Grup anahtarları benzersiz olmalı")
        return self


@dataclass(frozen=True)
class ResolvedGroup:
    definition: GroupDefinition
    indices: NDArray[np.int64]
    flywire_ids: tuple[int, ...]
    missing_ids: tuple[int, ...]  # tanımda olup modelde bulunamayan (ardılı da olmayan) kimlikler
    substituted: tuple[tuple[int, int], ...] = ()  # (referans kimliği, kullanılan ardıl)

    @property
    def size(self) -> int:
        return int(self.indices.size)


def load_group_definitions(path: Path = DEFAULT_GROUPS_PATH) -> dict[str, GroupDefinition]:
    with path.open("rb") as file:
        parsed = GroupFile.model_validate(tomllib.load(file))
    return {group.key: group for group in parsed.group}


def definitions_digest(definitions: dict[str, GroupDefinition] | None = None) -> str:
    """Nöron grubu TANIMLARININ özeti (yorumlar ve biçim değişiklikleri sonucu etkilemez).

    Hazır senaryo paketlerinin bütünlüğü bu özetle denetlenir: dosyadaki bir yorum satırı
    değiştiğinde paket geçersiz sayılmamalı, ama bir nöron kimliği ya da hücre tipi değiştiğinde
    sayılmalıdır.
    """
    items = definitions if definitions is not None else load_group_definitions()
    payload = [item.model_dump(mode="json") for _, item in sorted(items.items())]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def resolve_group(
    definition: GroupDefinition, connectome: Connectome | NeuronIndex, annotations: pd.DataFrame
) -> ResolvedGroup:
    if definition.selection == "reference_ids":
        candidates = list(definition.ids)
    else:
        mask = annotations["cell_type"].isin(definition.cell_types)
        candidates = sorted(int(i) for i in annotations.index[mask])

    indices, missing = connectome.index_of(candidates)
    # Veride bulunmayan referans kimliği için doğrulanmış ardılı varsa onu kullan.
    substituted = [
        (old, definition.successors[old]) for old in missing if old in definition.successors
    ]
    successor_indices, missing_successors = connectome.index_of([new for _, new in substituted])
    if missing_successors:
        raise ValueError(f"{definition.key}: ardıl kimlikler veride yok {missing_successors}")
    indices = np.concatenate([indices, successor_indices])
    return ResolvedGroup(
        definition=definition,
        indices=indices,
        flywire_ids=tuple(int(i) for i in connectome.flywire_ids[indices]),
        missing_ids=tuple(old for old in missing if old not in definition.successors),
        substituted=tuple(substituted),
    )


def resolve_groups(
    definitions: dict[str, GroupDefinition],
    connectome: Connectome | NeuronIndex,
    annotations: pd.DataFrame,
) -> dict[str, ResolvedGroup]:
    return {
        key: resolve_group(definition, connectome, annotations)
        for key, definition in definitions.items()
    }
