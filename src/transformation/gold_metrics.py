from collections import defaultdict
from datetime import timezone


VIDEO_COMMENT_METRICS_SCHEMA = {
    "video_id": "STRING",
    "comment_count": "BIGINT",
    "comment_like_count_total": "BIGINT",
    "comment_like_count_avg": "DOUBLE",
    "reply_count_total": "BIGINT",
    "reply_count_avg": "DOUBLE",
    "comments_with_replies_count": "BIGINT",
    "comments_with_replies_ratio": "DOUBLE",
    "distinct_author_name_count": "BIGINT",
    "first_published_at": "TIMESTAMP",
    "latest_published_at": "TIMESTAMP",
    "snapshot_at": "TIMESTAMP",
}

DAILY_COMMENT_METRICS_SCHEMA = {
    "video_id": "STRING",
    "comment_date": "DATE",
    "comment_count": "BIGINT",
    "comment_like_count_total": "BIGINT",
    "reply_count_total": "BIGINT",
    "comments_with_replies_count": "BIGINT",
    "comments_with_replies_ratio": "DOUBLE",
    "distinct_author_name_count": "BIGINT",
    "snapshot_at": "TIMESTAMP",
}


def _build_common_metrics(comments: list[dict]) -> dict:
    comment_count = len(comments)
    comment_like_count_total = sum(
        comment["like_count"] for comment in comments
    )
    reply_count_total = sum(
        comment["total_reply_count"] for comment in comments
    )
    comments_with_replies_count = sum(
        comment["total_reply_count"] > 0 for comment in comments
    )
    distinct_author_names = {
        comment["author_name"]
        for comment in comments
        if comment.get("author_name") is not None
    }

    return {
        "comment_count": comment_count,
        "comment_like_count_total": comment_like_count_total,
        "reply_count_total": reply_count_total,
        "comments_with_replies_count": comments_with_replies_count,
        "comments_with_replies_ratio": (
            comments_with_replies_count / comment_count
        ),
        "distinct_author_name_count": len(distinct_author_names),
        "snapshot_at": max(comment["ingested_at"] for comment in comments),
    }


def build_video_comment_metrics(comments: list[dict]) -> list[dict]:
    comments_by_video = defaultdict(list)

    for comment in comments:
        comments_by_video[comment["video_id"]].append(comment)

    metrics = []

    for video_id in sorted(comments_by_video):
        video_comments = comments_by_video[video_id]
        common_metrics = _build_common_metrics(video_comments)
        comment_count = common_metrics["comment_count"]
        metrics.append(
            {
                "video_id": video_id,
                "comment_count": comment_count,
                "comment_like_count_total": common_metrics[
                    "comment_like_count_total"
                ],
                "comment_like_count_avg": (
                    common_metrics["comment_like_count_total"]
                    / comment_count
                ),
                "reply_count_total": common_metrics["reply_count_total"],
                "reply_count_avg": (
                    common_metrics["reply_count_total"] / comment_count
                ),
                "comments_with_replies_count": common_metrics[
                    "comments_with_replies_count"
                ],
                "comments_with_replies_ratio": common_metrics[
                    "comments_with_replies_ratio"
                ],
                "distinct_author_name_count": common_metrics[
                    "distinct_author_name_count"
                ],
                "first_published_at": min(
                    comment["published_at"] for comment in video_comments
                ),
                "latest_published_at": max(
                    comment["published_at"] for comment in video_comments
                ),
                "snapshot_at": common_metrics["snapshot_at"],
            }
        )

    return metrics


def build_daily_comment_metrics(comments: list[dict]) -> list[dict]:
    comments_by_video_date = defaultdict(list)

    for comment in comments:
        comment_date = comment["published_at"].astimezone(
            timezone.utc
        ).date()
        group_key = (comment["video_id"], comment_date)
        comments_by_video_date[group_key].append(comment)

    metrics = []

    for video_id, comment_date in sorted(comments_by_video_date):
        daily_comments = comments_by_video_date[(video_id, comment_date)]
        common_metrics = _build_common_metrics(daily_comments)
        metrics.append(
            {
                "video_id": video_id,
                "comment_date": comment_date,
                "comment_count": common_metrics["comment_count"],
                "comment_like_count_total": common_metrics[
                    "comment_like_count_total"
                ],
                "reply_count_total": common_metrics["reply_count_total"],
                "comments_with_replies_count": common_metrics[
                    "comments_with_replies_count"
                ],
                "comments_with_replies_ratio": common_metrics[
                    "comments_with_replies_ratio"
                ],
                "distinct_author_name_count": common_metrics[
                    "distinct_author_name_count"
                ],
                "snapshot_at": common_metrics["snapshot_at"],
            }
        )

    return metrics
