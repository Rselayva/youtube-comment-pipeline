from datetime import datetime, timezone

import pytest

from enrichment.entity_aliases import load_entity_alias_dictionary
from enrichment.topic_keywords import load_topic_keyword_dictionary
from transformation.entity_sov_metrics import (
    build_daily_entity_sov_metrics,
    build_video_entity_sov_metrics,
)
from transformation.topic_metrics import (
    build_daily_topic_metrics,
    build_video_topic_metrics,
)
from validation.gold_validator import (
    validate_entity_sov_metrics,
    validate_topic_metrics,
)


ALIASES = load_entity_alias_dictionary()
TOPICS = load_topic_keyword_dictionary()
TIMESTAMP = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def make_comments() -> list[dict]:
    return [
        {
            "comment_id": "comment-1",
            "video_id": "video-1",
            "published_at": TIMESTAMP,
            "ingested_at": TIMESTAMP,
        },
        {
            "comment_id": "comment-2",
            "video_id": "video-1",
            "published_at": TIMESTAMP,
            "ingested_at": TIMESTAMP,
        },
    ]


def make_mentions() -> list[dict]:
    return [
        {
            "comment_id": "comment-1",
            "video_id": "video-1",
            "entity_type": "group",
            "entity_id": "nmixx",
            "group_id": "nmixx",
            "mention_count": 1,
            "dictionary_version": "nmixx_v2",
        },
        {
            "comment_id": "comment-1",
            "video_id": "video-1",
            "entity_type": "member",
            "entity_id": "nmixx_haewon",
            "group_id": "nmixx",
            "mention_count": 1,
            "dictionary_version": "nmixx_v2",
        },
    ]


def make_topic_records() -> list[dict]:
    return [
        {
            "comment_id": "comment-1",
            "video_id": "video-1",
            "topic_id": "vocal",
            "topic_count": 1,
            "dictionary_version": "comment_topics_v1",
        },
        {
            "comment_id": "comment-2",
            "video_id": "video-1",
            "topic_id": "dance",
            "topic_count": 1,
            "dictionary_version": "comment_topics_v1",
        },
    ]


def test_gold_validators_accept_builder_outputs():
    comments = make_comments()

    validate_entity_sov_metrics(
        build_video_entity_sov_metrics(comments, make_mentions(), ALIASES)
    )
    validate_entity_sov_metrics(
        build_daily_entity_sov_metrics(comments, make_mentions(), ALIASES),
        daily=True,
    )
    validate_topic_metrics(
        build_video_topic_metrics(comments, make_topic_records(), TOPICS)
    )
    validate_topic_metrics(
        build_daily_topic_metrics(comments, make_topic_records(), TOPICS),
        daily=True,
    )


def test_gold_validators_accept_empty_snapshots():
    validate_entity_sov_metrics([])
    validate_topic_metrics([])


def test_entity_validator_rejects_duplicate_logical_key():
    metrics = build_video_entity_sov_metrics(
        make_comments(), make_mentions(), ALIASES
    )
    metrics.append(metrics[0].copy())

    with pytest.raises(ValueError, match="Duplicate entity SOV logical key"):
        validate_entity_sov_metrics(metrics)


def test_entity_validator_rejects_inconsistent_group_denominator():
    metrics = build_video_entity_sov_metrics(
        make_comments(), make_mentions(), ALIASES
    )
    zero_member_metric = next(
        metric
        for metric in metrics
        if metric["entity_type"] == "member"
        and metric["mention_comment_count"] == 0
    )
    zero_member_metric["entity_type_mention_comment_count"] = 2

    with pytest.raises(
        ValueError,
        match="entity_type_mention_comment_count must be consistent",
    ):
        validate_entity_sov_metrics(metrics)


def test_topic_validator_rejects_ratio_mismatch():
    metrics = build_video_topic_metrics(
        make_comments(), make_topic_records(), TOPICS
    )
    metrics[0]["comment_share_of_voice"] = 0.25

    with pytest.raises(
        ValueError,
        match="comment_share_of_voice does not match",
    ):
        validate_topic_metrics(metrics)


def test_topic_validator_rejects_schema_drift():
    metrics = build_video_topic_metrics(
        make_comments(), make_topic_records(), TOPICS
    )
    metrics[0]["unexpected_field"] = "unexpected"

    with pytest.raises(ValueError, match="schema mismatch"):
        validate_topic_metrics(metrics)


def test_daily_topic_validator_rejects_non_date_partition():
    metrics = build_daily_topic_metrics(
        make_comments(), make_topic_records(), TOPICS
    )
    metrics[0]["comment_date"] = "2026-08-21"

    with pytest.raises(ValueError, match="comment_date must be a date"):
        validate_topic_metrics(metrics, daily=True)


def test_topic_validator_rejects_inconsistent_snapshot_comment_count():
    metrics = build_video_topic_metrics(
        make_comments(), make_topic_records(), TOPICS
    )
    metrics[0]["comment_count"] = 4
    metrics[0]["comment_share_of_voice"] = 0.25

    with pytest.raises(
        ValueError,
        match="comment_count must be consistent per snapshot",
    ):
        validate_topic_metrics(metrics)


def test_topic_validator_rejects_output_partition_mismatch():
    metrics = build_video_topic_metrics(
        make_comments(), make_topic_records(), TOPICS
    )

    with pytest.raises(
        ValueError,
        match="dictionary_version does not match output path",
    ):
        validate_topic_metrics(
            metrics,
            expected_video_id="video-1",
            expected_dictionary_version="comment_topics_v2",
        )
