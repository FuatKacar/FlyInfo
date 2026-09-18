from pathlib import Path

import pytest
from pydantic import ValidationError

from sinek.connectome.connectome import build_connectome, load_annotations
from sinek.connectome.groups import (
    Behavior,
    GroupDefinition,
    GroupRole,
    load_group_definitions,
    resolve_group,
)

Files = tuple[Path, Path, Path]


def definition(**overrides: object) -> GroupDefinition:
    fields: dict[str, object] = {
        "key": "test",
        "role": "stimulus",
        "name_tr": "Test",
        "description_tr": "Test grubu",
        "citations": [3],
        "selection": "reference_ids",
        "reference": "test",
        "ids": [1000, 1002, 424242],
    }
    fields.update(overrides)
    return GroupDefinition.model_validate(fields)


def test_referans_kimlikleri_cozumlenir_kayiplar_raporlanir(mini_files: Files) -> None:
    completeness, connectivity, annotations = mini_files
    c = build_connectome(completeness, connectivity)

    group = resolve_group(definition(), c, load_annotations(annotations))

    assert group.indices.tolist() == [0, 2]
    assert group.flywire_ids == (1000, 1002)
    assert group.missing_ids == (424242,)


def test_anotasyon_secimi_modelde_olmayani_kayip_sayar(mini_files: Files) -> None:
    completeness, connectivity, annotations = mini_files
    c = build_connectome(completeness, connectivity)

    group = resolve_group(
        definition(selection="annotation", ids=[], reference=None, cell_types=["B"]),
        c,
        load_annotations(annotations),
    )

    assert sorted(group.flywire_ids) == [1001, 1002]
    assert group.missing_ids == (9999,)


def test_kayip_kimlik_dogrulanmis_ardilla_degistirilir(mini_files: Files) -> None:
    completeness, connectivity, annotations = mini_files
    c = build_connectome(completeness, connectivity)

    group = resolve_group(
        definition(successors={424242: 1003}, successors_source="test"),
        c,
        load_annotations(annotations),
    )

    assert sorted(group.flywire_ids) == [1000, 1002, 1003]
    assert group.missing_ids == ()
    assert group.substituted == ((424242, 1003),)


def test_ardil_veride_yoksa_hata_verir(mini_files: Files) -> None:
    completeness, connectivity, annotations = mini_files
    c = build_connectome(completeness, connectivity)

    with pytest.raises(ValueError, match="ardıl kimlikler veride yok"):
        resolve_group(
            definition(successors={424242: 555}, successors_source="test"),
            c,
            load_annotations(annotations),
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"successors": {999: 1}, "successors_source": "x"}, "referans listesinde yok"),
        ({"successors": {1000: 1}}, "kaynağı belirtilmeli"),
        ({"ids": []}, "ids ve reference"),
        ({"selection": "annotation", "cell_types": []}, "cell_types"),
        ({"ids": [1, 1]}, "yinelenen"),
        ({"citations": []}, "kaynak"),
        ({"unknown_field": 1}, "Extra inputs"),
    ],
)
def test_gecersiz_tanimlar_reddedilir(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        definition(**overrides)


def test_proje_grup_dosyasi_gecerli_ve_tutarli() -> None:
    groups = load_group_definitions()

    stimulus = {k for k, g in groups.items() if g.role is GroupRole.STIMULUS}
    readout_behaviors = {g.behavior for g in groups.values() if g.role is GroupRole.READOUT}

    assert {"sugar", "bitter", "water", "johnston_organ", "looming", "geosmin", "co2"} <= stimulus
    assert set(Behavior) <= readout_behaviors  # her davranışın en az bir okuma nöronu var
    assert all(1 <= n <= 18 for g in groups.values() for n in g.citations)
