from collections import defaultdict
from datetime import timezone

from enrichment.entity_aliases import EntityAliasDictionary


VIDEO_ENTITY_SOV_SCHEMA = {
    "video_id": "STRING",
    "entity_type": "STRING",
    "entity_id": "STRING",
    "group_id": "STRING",
    "canonical_name": "STRING",
    "dictionary_version": "STRING",
    "comment_count": "BIGINT",
    "mention_comment_count": "BIGINT",
    "comment_share_of_voice": "DOUBLE",
    "entity_type_mention_comment_count": "BIGINT",
    "entity_share_of_voice": "DOUBLE",
    "snapshot_at": "TIMESTAMP",
}

DAILY_ENTITY_SOV_SCHEMA = {
    "video_id": "STRING",
    "comment_date": "DATE",
    "entity_type": "STRING",
    "entity_id": "STRING",
    "group_id": "STRING",
    "canonical_name": "STRING",
    "dictionary_version": "STRING",
    "comment_count": "BIGINT",
    "mention_comment_count": "BIGINT",
    "comment_share_of_voice": "DOUBLE",
    "entity_type_mention_comment_count": "BIGINT",
    "entity_share_of_voice": "DOUBLE",
    "snapshot_at": "TIMESTAMP",
}


def _build_entity_catalog(
    aliases: EntityAliasDictionary,
) -> list[dict]:
    groups = [
        {
            "entity_type": "group",
            "entity_id": group.group_id,
            "group_id": group.group_id,
            "canonical_name": group.canonical_name,
        }
        for group in aliases.groups_by_id.values()
    ]
    members = [
        {
            "entity_type": "member",
            "entity_id": member.member_id,
            "group_id": member.group_id,
            "canonical_name": member.canonical_name,
        }
        for member in aliases.members_by_id.values()
    ]
    return groups + members


def _index_comments(comments: list[dict]) -> dict[tuple[str, str], dict]:
    comments_by_key = {}

    for comment in comments:
        key = (comment["video_id"], comment["comment_id"])
        if key in comments_by_key:
            raise ValueError(
                "Comments must contain one latest row per video_id/comment_id"
            )
        comments_by_key[key] = comment

    return comments_by_key


def _validate_and_index_mentions(
    mentions: list[dict],
    comments_by_key: dict[tuple[str, str], dict],
    aliases: EntityAliasDictionary,
) -> dict[tuple[str, str], set[str]]:
    entity_catalog = {
        (entity["entity_type"], entity["entity_id"]): entity
        for entity in _build_entity_catalog(aliases)
    }
    comment_ids_by_video_entity = defaultdict(set)

    for mention in mentions:
        if mention["dictionary_version"] != aliases.dictionary_version:
            raise ValueError(
                "Mention dictionary_version does not match alias dictionary"
            )
        if mention["mention_count"] != 1:
            raise ValueError("mention_count must be 1 per comment/entity")

        entity_key = (mention["entity_type"], mention["entity_id"])
        entity = entity_catalog.get(entity_key)
        if entity is None:
            raise ValueError(f"Unknown mention entity: {entity_key}")
        if mention["group_id"] != entity["group_id"]:
            raise ValueError("Mention group_id does not match entity catalog")

        comment_key = (mention["video_id"], mention["comment_id"])
        if comment_key not in comments_by_key:
            raise ValueError("Mention references an unknown comment")

        count_key = (mention["video_id"], mention["entity_id"])
        comment_ids_by_video_entity[count_key].add(mention["comment_id"])

    return comment_ids_by_video_entity


def _build_metric_row(
    entity: dict,
    dictionary_version: str,
    comment_count: int,
    mention_comment_count: int,
    entity_type_mention_comment_count: int,
    snapshot_at,
) -> dict:
    return {
        **entity,
        "dictionary_version": dictionary_version,
        "comment_count": comment_count,
        "mention_comment_count": mention_comment_count,
        "comment_share_of_voice": mention_comment_count / comment_count,
        "entity_type_mention_comment_count": (
            entity_type_mention_comment_count
        ),
        "entity_share_of_voice": (
            mention_comment_count / entity_type_mention_comment_count
            if entity_type_mention_comment_count
            else 0.0
        ),
        "snapshot_at": snapshot_at,
    }


def build_video_entity_sov_metrics(
    comments: list[dict],
    mentions: list[dict],
    aliases: EntityAliasDictionary,
) -> list[dict]:
    if not comments:
        return []

    comments_by_key = _index_comments(comments)
    comment_ids_by_video_entity = _validate_and_index_mentions(
        mentions,
        comments_by_key,
        aliases,
    )
    comments_by_video = defaultdict(list)
    for comment in comments:
        comments_by_video[comment["video_id"]].append(comment)

    entity_catalog = _build_entity_catalog(aliases)
    metrics = []

    for video_id in sorted(comments_by_video):
        video_comments = comments_by_video[video_id]
        mention_counts = {
            entity["entity_id"]: len(
                comment_ids_by_video_entity[
                    (video_id, entity["entity_id"])
                ]
            )
            for entity in entity_catalog
        }
        type_totals = defaultdict(int)
        for entity in entity_catalog:
            type_totals[entity["entity_type"]] += mention_counts[
                entity["entity_id"]
            ]

        for entity in entity_catalog:
            metrics.append(
                {
                    "video_id": video_id,
                    **_build_metric_row(
                        entity=entity,
                        dictionary_version=aliases.dictionary_version,
                        comment_count=len(video_comments),
                        mention_comment_count=mention_counts[
                            entity["entity_id"]
                        ],
                        entity_type_mention_comment_count=type_totals[
                            entity["entity_type"]
                        ],
                        snapshot_at=max(
                            comment["ingested_at"]
                            for comment in video_comments
                        ),
                    ),
                }
            )

    return metrics


def build_daily_entity_sov_metrics(
    comments: list[dict],
    mentions: list[dict],
    aliases: EntityAliasDictionary,
) -> list[dict]:
    if not comments:
        return []

    comments_by_key = _index_comments(comments)
    _validate_and_index_mentions(mentions, comments_by_key, aliases)
    comments_by_video_date = defaultdict(list)
    for comment in comments:
        comment_date = comment["published_at"].astimezone(
            timezone.utc
        ).date()
        comments_by_video_date[(comment["video_id"], comment_date)].append(
            comment
        )

    mentions_by_comment = defaultdict(list)
    for mention in mentions:
        mentions_by_comment[
            (mention["video_id"], mention["comment_id"])
        ].append(mention)

    entity_catalog = _build_entity_catalog(aliases)
    metrics = []

    for video_id, comment_date in sorted(comments_by_video_date):
        daily_comments = comments_by_video_date[(video_id, comment_date)]
        daily_comment_ids = {
            comment["comment_id"] for comment in daily_comments
        }
        mentioned_comment_ids = defaultdict(set)
        for comment_id in daily_comment_ids:
            for mention in mentions_by_comment[(video_id, comment_id)]:
                mentioned_comment_ids[mention["entity_id"]].add(comment_id)

        mention_counts = {
            entity["entity_id"]: len(
                mentioned_comment_ids[entity["entity_id"]]
            )
            for entity in entity_catalog
        }
        type_totals = defaultdict(int)
        for entity in entity_catalog:
            type_totals[entity["entity_type"]] += mention_counts[
                entity["entity_id"]
            ]

        for entity in entity_catalog:
            metrics.append(
                {
                    "video_id": video_id,
                    "comment_date": comment_date,
                    **_build_metric_row(
                        entity=entity,
                        dictionary_version=aliases.dictionary_version,
                        comment_count=len(daily_comments),
                        mention_comment_count=mention_counts[
                            entity["entity_id"]
                        ],
                        entity_type_mention_comment_count=type_totals[
                            entity["entity_type"]
                        ],
                        snapshot_at=max(
                            comment["ingested_at"]
                            for comment in daily_comments
                        ),
                    ),
                }
            )

    return metrics
