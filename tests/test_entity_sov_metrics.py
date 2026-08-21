from datetime import datetime, timedelta, timezone

import pytest

from enrichment.entity_aliases import load_entity_alias_dictionary
from transformation.entity_sov_metrics import (
    DAILY_ENTITY_SOV_SCHEMA,
    VIDEO_ENTITY_SOV_SCHEMA,
    build_daily_entity_sov_metrics,
    build_video_entity_sov_metrics,
)


ALIASES = load_entity_alias_dictionary()
SNAPSHOT_AT = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def make_comment(
    comment_id: str,
    published_at: datetime,
    video_id: str = "video-1",
) -> dict:
    return {
        "comment_id": comment_id,
        "video_id": video_id,
        "published_at": published_at,
        "ingested_at": SNAPSHOT_AT,
    }


def make_mention(
    comment_id: str,
    entity_type: str,
    entity_id: str,
) -> dict:
    if entity_type == "group":
        group_id = entity_id
    else:
        group_id = ALIASES.members_by_id[entity_id].group_id

    return {
        "comment_id": comment_id,
        "video_id": "video-1",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "group_id": group_id,
        "mention_count": 1,
        "dictionary_version": "nmixx_v2",
    }


def test_build_video_entity_sov_metrics_calculates_each_type_separately():
    comments = [
        make_comment(
            "comment-1",
            datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
        ),
        make_comment(
            "comment-2",
            datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc),
        ),
        make_comment(
            "comment-3",
            datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc),
        ),
    ]
    mentions = [
        make_mention("comment-1", "group", "nmixx"),
        make_mention("comment-1", "member", "nmixx_haewon"),
        make_mention("comment-2", "member", "nmixx_haewon"),
        make_mention("comment-3", "member", "nmixx_lily"),
    ]

    metrics = build_video_entity_sov_metrics(comments, mentions, ALIASES)
    metrics_by_entity = {
        metric["entity_id"]: metric for metric in metrics
    }

    assert len(metrics) == 7
    assert metrics_by_entity["nmixx"]["mention_comment_count"] == 1
    assert metrics_by_entity["nmixx"]["comment_share_of_voice"] == 1 / 3
    assert metrics_by_entity["nmixx"]["entity_share_of_voice"] == 1.0
    assert metrics_by_entity["nmixx_haewon"]["mention_comment_count"] == 2
    assert (
        metrics_by_entity["nmixx_haewon"]["comment_share_of_voice"]
        == 2 / 3
    )
    assert (
        metrics_by_entity["nmixx_haewon"][
            "entity_type_mention_comment_count"
        ]
        == 3
    )
    assert metrics_by_entity["nmixx_haewon"]["entity_share_of_voice"] == 2 / 3
    assert metrics_by_entity["nmixx_lily"]["entity_share_of_voice"] == 1 / 3
    assert metrics_by_entity["nmixx_kyujin"]["mention_comment_count"] == 0
    assert metrics_by_entity["nmixx_kyujin"]["entity_share_of_voice"] == 0.0


def test_build_video_entity_sov_metrics_deduplicates_comment_entity_rows():
    comments = [
        make_comment(
            "comment-1",
            datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
        )
    ]
    mention = make_mention("comment-1", "member", "nmixx_haewon")

    metrics = build_video_entity_sov_metrics(
        comments,
        [mention, mention.copy()],
        ALIASES,
    )
    haewon_metric = next(
        metric
        for metric in metrics
        if metric["entity_id"] == "nmixx_haewon"
    )

    assert haewon_metric["mention_comment_count"] == 1
    assert haewon_metric["entity_type_mention_comment_count"] == 1


def test_build_daily_entity_sov_metrics_uses_utc_dates():
    taipei_timezone = timezone(timedelta(hours=8))
    comments = [
        make_comment(
            "comment-1",
            datetime(2026, 8, 21, 7, 30, tzinfo=taipei_timezone),
        ),
        make_comment(
            "comment-2",
            datetime(2026, 8, 21, 1, 0, tzinfo=timezone.utc),
        ),
    ]
    mentions = [
        make_mention("comment-1", "member", "nmixx_lily"),
        make_mention("comment-2", "member", "nmixx_haewon"),
    ]

    metrics = build_daily_entity_sov_metrics(comments, mentions, ALIASES)

    assert len(metrics) == 14
    lily_metrics = [
        metric for metric in metrics if metric["entity_id"] == "nmixx_lily"
    ]
    assert [metric["comment_date"].isoformat() for metric in lily_metrics] == [
        "2026-08-20",
        "2026-08-21",
    ]
    assert [metric["mention_comment_count"] for metric in lily_metrics] == [
        1,
        0,
    ]


def test_entity_sov_metrics_reject_non_unique_mention_count():
    comments = [
        make_comment(
            "comment-1",
            datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
        )
    ]
    mention = make_mention("comment-1", "member", "nmixx_haewon")
    mention["mention_count"] = 2

    with pytest.raises(
        ValueError,
        match="mention_count must be 1 per comment/entity",
    ):
        build_video_entity_sov_metrics(comments, [mention], ALIASES)


def test_entity_sov_metric_builders_return_empty_for_no_comments():
    assert build_video_entity_sov_metrics([], [], ALIASES) == []
    assert build_daily_entity_sov_metrics([], [], ALIASES) == []


def test_entity_sov_schemas_match_output_columns():
    comment = make_comment(
        "comment-1",
        datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
    )

    video_metric = build_video_entity_sov_metrics(
        [comment], [], ALIASES
    )[0]
    daily_metric = build_daily_entity_sov_metrics(
        [comment], [], ALIASES
    )[0]

    assert tuple(video_metric) == tuple(VIDEO_ENTITY_SOV_SCHEMA)
    assert tuple(daily_metric) == tuple(DAILY_ENTITY_SOV_SCHEMA)
