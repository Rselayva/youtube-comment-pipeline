import json

import pytest

from enrichment.entity_aliases import (
    load_entity_alias_dictionary,
    normalize_alias,
)


def make_dictionary():
    return {
        "schema_version": 1,
        "dictionary_version": "test_v1",
        "description": "Test alias dictionary.",
        "groups": [
            {
                "group_id": "group_a",
                "canonical_name": "Group A",
                "aliases": ["그룹에이"],
            }
        ],
        "members": [
            {
                "member_id": "member_a",
                "group_id": "group_a",
                "canonical_name": "Member A",
                "aliases": ["멤버에이"],
            }
        ],
    }


def write_dictionary(tmp_path, raw_dictionary):
    path = tmp_path / "entity_aliases.json"
    path.write_text(
        json.dumps(raw_dictionary, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_load_nmxx_alias_dictionary():
    aliases = load_entity_alias_dictionary()

    assert aliases.schema_version == 1
    assert aliases.dictionary_version == "nmixx_v2"
    assert aliases.description == (
        "目前為開發階段使用的關鍵詞版本；"
        "未來可依需求建立新版本，加入更多相關暱稱。"
    )
    assert tuple(aliases.groups_by_id) == ("nmixx",)
    assert tuple(aliases.members_by_id) == (
        "nmixx_lily",
        "nmixx_haewon",
        "nmixx_sullyoon",
        "nmixx_bae",
        "nmixx_jiwoo",
        "nmixx_kyujin",
    )
    assert aliases.group_alias_to_id["nmixx"] == "nmixx"
    assert aliases.group_alias_to_id["엔믹스"] == "nmixx"
    assert aliases.member_alias_to_id["lily"] == "nmixx_lily"
    assert aliases.member_alias_to_id["릴리"] == "nmixx_lily"
    assert aliases.member_alias_to_id["莉"] == "nmixx_lily"
    assert aliases.member_alias_to_id["莉莉"] == "nmixx_lily"
    assert aliases.member_alias_to_id["朴珍"] == "nmixx_lily"
    assert aliases.member_alias_to_id["嫄"] == "nmixx_haewon"
    assert aliases.member_alias_to_id["海嫄"] == "nmixx_haewon"
    assert aliases.member_alias_to_id["吳海嫄"] == "nmixx_haewon"
    assert aliases.member_alias_to_id["薛"] == "nmixx_sullyoon"
    assert aliases.member_alias_to_id["侖娥"] == "nmixx_sullyoon"
    assert aliases.member_alias_to_id["薛侖娥"] == "nmixx_sullyoon"
    assert aliases.member_alias_to_id["裴"] == "nmixx_bae"
    assert aliases.member_alias_to_id["眞率"] == "nmixx_bae"
    assert aliases.member_alias_to_id["裴眞率"] == "nmixx_bae"
    assert aliases.member_alias_to_id["啾"] == "nmixx_jiwoo"
    assert aliases.member_alias_to_id["智佑"] == "nmixx_jiwoo"
    assert aliases.member_alias_to_id["金智佑"] == "nmixx_jiwoo"
    assert aliases.member_alias_to_id["圭"] == "nmixx_kyujin"
    assert aliases.member_alias_to_id["圭珍"] == "nmixx_kyujin"
    assert aliases.member_alias_to_id["張圭珍"] == "nmixx_kyujin"
    assert aliases.members_by_id["nmixx_lily"].group_id == "nmixx"


def test_normalize_alias_uses_nfkc_casefold_and_whitespace_collapse():
    assert normalize_alias("  ＮＭＩＸＸ  ") == "nmixx"
    assert normalize_alias("Member   A") == "member a"


def test_load_entity_alias_dictionary_rejects_unknown_member_group(tmp_path):
    raw_dictionary = make_dictionary()
    raw_dictionary["members"][0]["group_id"] = "missing_group"
    path = write_dictionary(tmp_path, raw_dictionary)

    with pytest.raises(
        ValueError,
        match="references unknown group_id: missing_group",
    ):
        load_entity_alias_dictionary(path)


def test_load_entity_alias_dictionary_rejects_duplicate_normalized_alias(
    tmp_path,
):
    raw_dictionary = make_dictionary()
    raw_dictionary["groups"][0]["aliases"].append("  GROUP A  ")
    path = write_dictionary(tmp_path, raw_dictionary)

    with pytest.raises(ValueError, match="contains duplicate alias"):
        load_entity_alias_dictionary(path)


def test_load_entity_alias_dictionary_rejects_cross_entity_alias_conflict(
    tmp_path,
):
    raw_dictionary = make_dictionary()
    raw_dictionary["members"][0]["aliases"].append("ＧＲＯＵＰ Ａ")
    path = write_dictionary(tmp_path, raw_dictionary)

    with pytest.raises(
        ValueError,
        match=r"conflicts with group\[group_a\]",
    ):
        load_entity_alias_dictionary(path)


def test_load_entity_alias_dictionary_rejects_unsupported_schema(tmp_path):
    raw_dictionary = make_dictionary()
    raw_dictionary["schema_version"] = 2
    path = write_dictionary(tmp_path, raw_dictionary)

    with pytest.raises(
        ValueError,
        match="Unsupported alias dictionary schema_version: 2",
    ):
        load_entity_alias_dictionary(path)
