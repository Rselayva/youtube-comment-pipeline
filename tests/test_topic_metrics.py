from datetime import datetime, timedelta, timezone

import pytest

from enrichment.topic_keywords import load_topic_keyword_dictionary
from transformation.topic_metrics import (
    DAILY_TOPIC_METRICS_SCHEMA,
    VIDEO_TOPIC_METRICS_SCHEMA,
    build_daily_topic_metrics,
    build_video_topic_metrics,
)


TOPICS = load_topic_keyword_dictionary()
SNAPSHOT_AT = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def make_comment(comment_id: str, published_at: datetime) -> dict:
    return {
        "comment_id": comment_id,
        "video_id": "video-1",
        "published_at": published_at,
        "ingested_at": SNAPSHOT_AT,
    }


def make_topic_record(comment_id: str, topic_id: str) -> dict:
    return {
        "comment_id": comment_id,
        "video_id": "video-1",
        "topic_id": topic_id,
        "topic_count": 1,
        "dictionary_version": "comment_topics_v1",
    }


def test_build_video_topic_metrics_calculates_comment_and_topic_shares():
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
    topic_records = [
        make_topic_record("comment-1", "vocal"),
        make_topic_record("comment-1", "dance"),
        make_topic_record("comment-2", "vocal"),
    ]

    metrics = build_video_topic_metrics(comments, topic_records, TOPICS)
    metrics_by_topic = {
        metric["topic_id"]: metric for metric in metrics
    }

    assert len(metrics) == 3
    assert metrics_by_topic["vocal"]["topic_comment_count"] == 2
    assert metrics_by_topic["vocal"]["comment_share_of_voice"] == 2 / 3
    assert metrics_by_topic["vocal"]["topic_comment_count_total"] == 3
    assert metrics_by_topic["vocal"]["topic_share_of_voice"] == 2 / 3
    assert metrics_by_topic["dance"]["topic_share_of_voice"] == 1 / 3
    assert metrics_by_topic["visual"]["topic_comment_count"] == 0
    assert metrics_by_topic["visual"]["topic_share_of_voice"] == 0.0


def test_build_video_topic_metrics_deduplicates_comment_topic_rows():
    comments = [
        make_comment(
            "comment-1",
            datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
        )
    ]
    topic_record = make_topic_record("comment-1", "vocal")

    metrics = build_video_topic_metrics(
        comments,
        [topic_record, topic_record.copy()],
        TOPICS,
    )
    vocal_metric = next(
        metric for metric in metrics if metric["topic_id"] == "vocal"
    )

    assert vocal_metric["topic_comment_count"] == 1
    assert vocal_metric["topic_comment_count_total"] == 1


def test_build_daily_topic_metrics_uses_utc_dates_and_zero_rows():
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
    topic_records = [
        make_topic_record("comment-1", "vocal"),
        make_topic_record("comment-2", "dance"),
    ]

    metrics = build_daily_topic_metrics(comments, topic_records, TOPICS)

    assert len(metrics) == 6
    vocal_metrics = [
        metric for metric in metrics if metric["topic_id"] == "vocal"
    ]
    assert [metric["comment_date"].isoformat() for metric in vocal_metrics] == [
        "2026-08-20",
        "2026-08-21",
    ]
    assert [metric["topic_comment_count"] for metric in vocal_metrics] == [
        1,
        0,
    ]


def test_topic_metrics_reject_non_unique_topic_count():
    comments = [
        make_comment(
            "comment-1",
            datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
        )
    ]
    topic_record = make_topic_record("comment-1", "vocal")
    topic_record["topic_count"] = 2

    with pytest.raises(
        ValueError,
        match="topic_count must be 1 per comment/topic",
    ):
        build_video_topic_metrics(comments, [topic_record], TOPICS)


def test_topic_metric_builders_return_empty_for_no_comments():
    assert build_video_topic_metrics([], [], TOPICS) == []
    assert build_daily_topic_metrics([], [], TOPICS) == []


def test_topic_metric_schemas_match_output_columns():
    comment = make_comment(
        "comment-1",
        datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
    )

    video_metric = build_video_topic_metrics([comment], [], TOPICS)[0]
    daily_metric = build_daily_topic_metrics([comment], [], TOPICS)[0]

    assert tuple(video_metric) == tuple(VIDEO_TOPIC_METRICS_SCHEMA)
    assert tuple(daily_metric) == tuple(DAILY_TOPIC_METRICS_SCHEMA)
