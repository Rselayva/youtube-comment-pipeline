from datetime import datetime, timedelta, timezone

from transformation.gold_metrics import (
    DAILY_COMMENT_METRICS_SCHEMA,
    VIDEO_COMMENT_METRICS_SCHEMA,
    build_daily_comment_metrics,
    build_video_comment_metrics,
)


def make_comment(
    comment_id: str,
    video_id: str,
    author_name: str | None,
    like_count: int,
    total_reply_count: int,
    published_at: datetime,
    ingested_at: datetime,
) -> dict:
    return {
        "comment_id": comment_id,
        "video_id": video_id,
        "author_name": author_name,
        "comment_text": "Test comment",
        "like_count": like_count,
        "total_reply_count": total_reply_count,
        "published_at": published_at,
        "updated_at": published_at,
        "ingested_at": ingested_at,
    }


def test_build_video_comment_metrics_calculates_audience_kpis():
    snapshot_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    comments = [
        make_comment(
            "comment-1",
            "video-1",
            "Author A",
            like_count=4,
            total_reply_count=2,
            published_at=datetime(
                2026, 8, 19, 8, 0, tzinfo=timezone.utc
            ),
            ingested_at=snapshot_at,
        ),
        make_comment(
            "comment-2",
            "video-1",
            "Author A",
            like_count=2,
            total_reply_count=0,
            published_at=datetime(
                2026, 8, 20, 9, 0, tzinfo=timezone.utc
            ),
            ingested_at=snapshot_at,
        ),
        make_comment(
            "comment-3",
            "video-1",
            None,
            like_count=0,
            total_reply_count=1,
            published_at=datetime(
                2026, 8, 21, 10, 0, tzinfo=timezone.utc
            ),
            ingested_at=snapshot_at,
        ),
    ]

    metrics = build_video_comment_metrics(comments)

    assert metrics == [
        {
            "video_id": "video-1",
            "comment_count": 3,
            "comment_like_count_total": 6,
            "comment_like_count_avg": 2.0,
            "reply_count_total": 3,
            "reply_count_avg": 1.0,
            "comments_with_replies_count": 2,
            "comments_with_replies_ratio": 2 / 3,
            "distinct_author_name_count": 1,
            "first_published_at": datetime(
                2026, 8, 19, 8, 0, tzinfo=timezone.utc
            ),
            "latest_published_at": datetime(
                2026, 8, 21, 10, 0, tzinfo=timezone.utc
            ),
            "snapshot_at": snapshot_at,
        }
    ]


def test_build_daily_comment_metrics_groups_by_utc_date_and_video():
    snapshot_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    taipei_timezone = timezone(timedelta(hours=8))
    comments = [
        make_comment(
            "comment-1",
            "video-2",
            "Author B",
            like_count=1,
            total_reply_count=0,
            published_at=datetime(
                2026, 8, 21, 1, 0, tzinfo=timezone.utc
            ),
            ingested_at=snapshot_at,
        ),
        make_comment(
            "comment-2",
            "video-1",
            "Author A",
            like_count=3,
            total_reply_count=2,
            published_at=datetime(
                2026, 8, 21, 7, 30, tzinfo=taipei_timezone
            ),
            ingested_at=snapshot_at,
        ),
    ]

    metrics = build_daily_comment_metrics(comments)

    assert [metric["video_id"] for metric in metrics] == [
        "video-1",
        "video-2",
    ]
    assert metrics[0]["comment_date"].isoformat() == "2026-08-20"
    assert metrics[0]["reply_count_total"] == 2
    assert metrics[0]["comments_with_replies_ratio"] == 1.0
    assert metrics[1]["comment_date"].isoformat() == "2026-08-21"


def test_gold_metric_builders_return_empty_for_no_comments():
    assert build_video_comment_metrics([]) == []
    assert build_daily_comment_metrics([]) == []


def test_gold_metric_schemas_match_output_columns():
    snapshot_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    comment = make_comment(
        "comment-1",
        "video-1",
        "Author A",
        like_count=1,
        total_reply_count=0,
        published_at=snapshot_at,
        ingested_at=snapshot_at,
    )

    video_metrics = build_video_comment_metrics([comment])[0]
    daily_metrics = build_daily_comment_metrics([comment])[0]

    assert tuple(video_metrics) == tuple(VIDEO_COMMENT_METRICS_SCHEMA)
    assert tuple(daily_metrics) == tuple(DAILY_COMMENT_METRICS_SCHEMA)
