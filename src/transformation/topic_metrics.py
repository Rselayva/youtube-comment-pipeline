from collections import defaultdict
from datetime import timezone

from enrichment.topic_keywords import TopicKeywordDictionary


VIDEO_TOPIC_METRICS_SCHEMA = {
    "video_id": "STRING",
    "topic_id": "STRING",
    "display_name": "STRING",
    "dictionary_version": "STRING",
    "comment_count": "BIGINT",
    "topic_comment_count": "BIGINT",
    "comment_share_of_voice": "DOUBLE",
    "topic_comment_count_total": "BIGINT",
    "topic_share_of_voice": "DOUBLE",
    "snapshot_at": "TIMESTAMP",
}

DAILY_TOPIC_METRICS_SCHEMA = {
    "video_id": "STRING",
    "comment_date": "DATE",
    "topic_id": "STRING",
    "display_name": "STRING",
    "dictionary_version": "STRING",
    "comment_count": "BIGINT",
    "topic_comment_count": "BIGINT",
    "comment_share_of_voice": "DOUBLE",
    "topic_comment_count_total": "BIGINT",
    "topic_share_of_voice": "DOUBLE",
    "snapshot_at": "TIMESTAMP",
}


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


def _validate_and_index_topic_records(
    topic_records: list[dict],
    comments_by_key: dict[tuple[str, str], dict],
    topics: TopicKeywordDictionary,
) -> dict[tuple[str, str], set[str]]:
    comment_ids_by_video_topic = defaultdict(set)

    for topic_record in topic_records:
        if topic_record["dictionary_version"] != topics.dictionary_version:
            raise ValueError(
                "Topic dictionary_version does not match topic dictionary"
            )
        if topic_record["topic_count"] != 1:
            raise ValueError("topic_count must be 1 per comment/topic")

        topic_id = topic_record["topic_id"]
        if topic_id not in topics.topics_by_id:
            raise ValueError(f"Unknown topic_id: {topic_id}")

        comment_key = (
            topic_record["video_id"],
            topic_record["comment_id"],
        )
        if comment_key not in comments_by_key:
            raise ValueError("Topic record references an unknown comment")

        count_key = (topic_record["video_id"], topic_id)
        comment_ids_by_video_topic[count_key].add(
            topic_record["comment_id"]
        )

    return comment_ids_by_video_topic


def _build_metric_row(
    topic,
    dictionary_version: str,
    comment_count: int,
    topic_comment_count: int,
    topic_comment_count_total: int,
    snapshot_at,
) -> dict:
    return {
        "topic_id": topic.topic_id,
        "display_name": topic.display_name,
        "dictionary_version": dictionary_version,
        "comment_count": comment_count,
        "topic_comment_count": topic_comment_count,
        "comment_share_of_voice": topic_comment_count / comment_count,
        "topic_comment_count_total": topic_comment_count_total,
        "topic_share_of_voice": (
            topic_comment_count / topic_comment_count_total
            if topic_comment_count_total
            else 0.0
        ),
        "snapshot_at": snapshot_at,
    }


def build_video_topic_metrics(
    comments: list[dict],
    topic_records: list[dict],
    topics: TopicKeywordDictionary,
) -> list[dict]:
    if not comments:
        return []

    comments_by_key = _index_comments(comments)
    comment_ids_by_video_topic = _validate_and_index_topic_records(
        topic_records,
        comments_by_key,
        topics,
    )
    comments_by_video = defaultdict(list)
    for comment in comments:
        comments_by_video[comment["video_id"]].append(comment)

    metrics = []
    for video_id in sorted(comments_by_video):
        video_comments = comments_by_video[video_id]
        topic_counts = {
            topic_id: len(
                comment_ids_by_video_topic[(video_id, topic_id)]
            )
            for topic_id in topics.topics_by_id
        }
        topic_count_total = sum(topic_counts.values())

        for topic in topics.topics_by_id.values():
            metrics.append(
                {
                    "video_id": video_id,
                    **_build_metric_row(
                        topic=topic,
                        dictionary_version=topics.dictionary_version,
                        comment_count=len(video_comments),
                        topic_comment_count=topic_counts[topic.topic_id],
                        topic_comment_count_total=topic_count_total,
                        snapshot_at=max(
                            comment["ingested_at"]
                            for comment in video_comments
                        ),
                    ),
                }
            )

    return metrics


def build_daily_topic_metrics(
    comments: list[dict],
    topic_records: list[dict],
    topics: TopicKeywordDictionary,
) -> list[dict]:
    if not comments:
        return []

    comments_by_key = _index_comments(comments)
    _validate_and_index_topic_records(
        topic_records,
        comments_by_key,
        topics,
    )
    comments_by_video_date = defaultdict(list)
    for comment in comments:
        comment_date = comment["published_at"].astimezone(
            timezone.utc
        ).date()
        comments_by_video_date[(comment["video_id"], comment_date)].append(
            comment
        )

    records_by_comment = defaultdict(list)
    for topic_record in topic_records:
        records_by_comment[
            (topic_record["video_id"], topic_record["comment_id"])
        ].append(topic_record)

    metrics = []
    for video_id, comment_date in sorted(comments_by_video_date):
        daily_comments = comments_by_video_date[(video_id, comment_date)]
        daily_comment_ids = {
            comment["comment_id"] for comment in daily_comments
        }
        mentioned_comment_ids = defaultdict(set)
        for comment_id in daily_comment_ids:
            for topic_record in records_by_comment[(video_id, comment_id)]:
                mentioned_comment_ids[topic_record["topic_id"]].add(
                    comment_id
                )

        topic_counts = {
            topic_id: len(mentioned_comment_ids[topic_id])
            for topic_id in topics.topics_by_id
        }
        topic_count_total = sum(topic_counts.values())

        for topic in topics.topics_by_id.values():
            metrics.append(
                {
                    "video_id": video_id,
                    "comment_date": comment_date,
                    **_build_metric_row(
                        topic=topic,
                        dictionary_version=topics.dictionary_version,
                        comment_count=len(daily_comments),
                        topic_comment_count=topic_counts[topic.topic_id],
                        topic_comment_count_total=topic_count_total,
                        snapshot_at=max(
                            comment["ingested_at"]
                            for comment in daily_comments
                        ),
                    ),
                }
            )

    return metrics
