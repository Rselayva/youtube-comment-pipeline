import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ENTITY_ALIASES_PATH = Path("config/entity_aliases.json")
SUPPORTED_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class GroupAlias:
    group_id: str
    canonical_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class MemberAlias:
    member_id: str
    group_id: str
    canonical_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class EntityAliasDictionary:
    schema_version: int
    dictionary_version: str
    groups_by_id: dict[str, GroupAlias]
    members_by_id: dict[str, MemberAlias]
    group_alias_to_id: dict[str, str]
    member_alias_to_id: dict[str, str]


def normalize_alias(value: str) -> str:
    normalized_value = unicodedata.normalize("NFKC", value)
    return " ".join(normalized_value.casefold().split())


def _require_non_empty_string(value, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")

    return value.strip()


def _load_aliases(
    raw_aliases,
    canonical_name: str,
    entity_label: str,
) -> tuple[str, ...]:
    if not isinstance(raw_aliases, list):
        raise ValueError(f"{entity_label}.aliases must be a list")

    aliases = [canonical_name]
    aliases.extend(raw_aliases)
    cleaned_aliases = []
    normalized_aliases = set()

    for alias in aliases:
        alias_value = _require_non_empty_string(
            alias,
            f"{entity_label}.alias",
        )
        normalized_alias = normalize_alias(alias_value)

        if normalized_alias in normalized_aliases:
            raise ValueError(
                f"{entity_label} contains duplicate alias: {alias_value}"
            )

        normalized_aliases.add(normalized_alias)
        cleaned_aliases.append(alias_value)

    return tuple(cleaned_aliases)


def _register_aliases(
    alias_to_entity_id: dict[str, str],
    global_alias_owners: dict[str, str],
    aliases: tuple[str, ...],
    entity_id: str,
    entity_label: str,
) -> None:
    for alias in aliases:
        normalized_alias = normalize_alias(alias)
        existing_owner = global_alias_owners.get(normalized_alias)

        if existing_owner is not None:
            raise ValueError(
                f"Alias '{alias}' conflicts with {existing_owner}"
            )

        global_alias_owners[normalized_alias] = entity_label
        alias_to_entity_id[normalized_alias] = entity_id


def load_entity_alias_dictionary(
    path: Path = DEFAULT_ENTITY_ALIASES_PATH,
) -> EntityAliasDictionary:
    with path.open(encoding="utf-8") as input_file:
        raw_dictionary = json.load(input_file)

    schema_version = raw_dictionary.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported alias dictionary schema_version: "
            f"{schema_version}"
        )

    dictionary_version = _require_non_empty_string(
        raw_dictionary.get("dictionary_version"),
        "dictionary_version",
    )
    raw_groups = raw_dictionary.get("groups")
    raw_members = raw_dictionary.get("members")

    if not isinstance(raw_groups, list) or not raw_groups:
        raise ValueError("groups must be a non-empty list")

    if not isinstance(raw_members, list):
        raise ValueError("members must be a list")

    groups_by_id = {}
    members_by_id = {}
    group_alias_to_id = {}
    member_alias_to_id = {}
    global_alias_owners = {}

    for raw_group in raw_groups:
        group_id = _require_non_empty_string(
            raw_group.get("group_id"),
            "group.group_id",
        )

        if group_id in groups_by_id:
            raise ValueError(f"Duplicate group_id: {group_id}")

        canonical_name = _require_non_empty_string(
            raw_group.get("canonical_name"),
            f"group[{group_id}].canonical_name",
        )
        aliases = _load_aliases(
            raw_group.get("aliases"),
            canonical_name,
            f"group[{group_id}]",
        )
        group = GroupAlias(
            group_id=group_id,
            canonical_name=canonical_name,
            aliases=aliases,
        )
        groups_by_id[group_id] = group
        _register_aliases(
            group_alias_to_id,
            global_alias_owners,
            aliases,
            group_id,
            f"group[{group_id}]",
        )

    for raw_member in raw_members:
        member_id = _require_non_empty_string(
            raw_member.get("member_id"),
            "member.member_id",
        )

        if member_id in members_by_id:
            raise ValueError(f"Duplicate member_id: {member_id}")

        group_id = _require_non_empty_string(
            raw_member.get("group_id"),
            f"member[{member_id}].group_id",
        )
        if group_id not in groups_by_id:
            raise ValueError(
                f"member[{member_id}] references unknown group_id: "
                f"{group_id}"
            )

        canonical_name = _require_non_empty_string(
            raw_member.get("canonical_name"),
            f"member[{member_id}].canonical_name",
        )
        aliases = _load_aliases(
            raw_member.get("aliases"),
            canonical_name,
            f"member[{member_id}]",
        )
        member = MemberAlias(
            member_id=member_id,
            group_id=group_id,
            canonical_name=canonical_name,
            aliases=aliases,
        )
        members_by_id[member_id] = member
        _register_aliases(
            member_alias_to_id,
            global_alias_owners,
            aliases,
            member_id,
            f"member[{member_id}]",
        )

    return EntityAliasDictionary(
        schema_version=schema_version,
        dictionary_version=dictionary_version,
        groups_by_id=groups_by_id,
        members_by_id=members_by_id,
        group_alias_to_id=group_alias_to_id,
        member_alias_to_id=member_alias_to_id,
    )
