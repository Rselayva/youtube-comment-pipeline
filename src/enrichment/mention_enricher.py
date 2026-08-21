import re

from enrichment.entity_aliases import (
    EntityAliasDictionary,
    normalize_alias,
)


def count_alias_mentions(
    comment_text: str,
    alias: str,
) -> int:
    normalized_text = normalize_alias(comment_text)
    normalized_alias = normalize_alias(alias)
    escaped_alias = re.escape(normalized_alias)

    if normalized_alias.isascii():
        pattern = rf"(?<![A-Za-z0-9_]){escaped_alias}(?![A-Za-z0-9_])"
    else:
        pattern = escaped_alias

    return len(re.findall(pattern, normalized_text))


def _find_alias_spans(
    normalized_text: str,
    alias: str,
) -> list[tuple[int, int]]:
    normalized_alias = normalize_alias(alias)
    escaped_alias = re.escape(normalized_alias)

    if normalized_alias.isascii():
        pattern = rf"(?<![A-Za-z0-9_]){escaped_alias}(?![A-Za-z0-9_])"
    else:
        pattern = escaped_alias

    return [match.span() for match in re.finditer(pattern, normalized_text)]


def _find_entity_matched_aliases(
    comment_text: str,
    entity_aliases: tuple[str, ...],
) -> tuple[str, ...]:
    normalized_text = normalize_alias(comment_text)
    candidates = [
        (start, end, alias)
        for alias in entity_aliases
        for start, end in _find_alias_spans(normalized_text, alias)
    ]
    candidates.sort(key=lambda candidate: (-(candidate[1] - candidate[0]), candidate[0]))

    selected_spans = []
    matched_aliases = set()

    for start, end, alias in candidates:
        if any(
            start < selected_end and selected_start < end
            for selected_start, selected_end in selected_spans
        ):
            continue

        selected_spans.append((start, end))
        matched_aliases.add(alias)

    return tuple(
        alias for alias in entity_aliases if alias in matched_aliases
    )


def enrich_comment_mentions(
    comment: dict,
    aliases: EntityAliasDictionary,
) -> list[dict]:
    comment_text = comment.get("comment_text")

    if not isinstance(comment_text, str):
        raise ValueError("comment_text must be a string")

    mention_records = []

    for group in aliases.groups_by_id.values():
        matched_aliases = _find_entity_matched_aliases(
            comment_text,
            group.aliases,
        )
        if matched_aliases:
            mention_records.append(
                {
                    "comment_id": comment["comment_id"],
                    "video_id": comment["video_id"],
                    "entity_type": "group",
                    "entity_id": group.group_id,
                    "group_id": group.group_id,
                    "canonical_name": group.canonical_name,
                    "matched_aliases": matched_aliases,
                    "mention_count": 1,
                    "published_at": comment["published_at"],
                    "ingested_at": comment["ingested_at"],
                    "dictionary_version": aliases.dictionary_version,
                }
            )

    for member in aliases.members_by_id.values():
        matched_aliases = _find_entity_matched_aliases(
            comment_text,
            member.aliases,
        )
        if matched_aliases:
            mention_records.append(
                {
                    "comment_id": comment["comment_id"],
                    "video_id": comment["video_id"],
                    "entity_type": "member",
                    "entity_id": member.member_id,
                    "group_id": member.group_id,
                    "canonical_name": member.canonical_name,
                    "matched_aliases": matched_aliases,
                    "mention_count": 1,
                    "published_at": comment["published_at"],
                    "ingested_at": comment["ingested_at"],
                    "dictionary_version": aliases.dictionary_version,
                }
            )

    return mention_records


def enrich_comment_dataset_mentions(
    comments: list[dict],
    aliases: EntityAliasDictionary,
) -> list[dict]:
    return [
        mention
        for comment in comments
        for mention in enrich_comment_mentions(comment, aliases)
    ]
