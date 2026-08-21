from datetime import datetime, timezone

import pytest

from enrichment.topic_enricher import (
    enrich_comment_dataset_topics,
    enrich_comment_topics,
)
from enrichment.topic_keywords import load_topic_keyword_dictionary


TOPICS = load_topic_keyword_dictionary()
TIMESTAMP = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)


def make_comment(comment_id: str, comment_text: str) -> dict:
    return {
        "comment_id": comment_id,
        "video_id": "video-1",
        "comment_text": comment_text,
        "published_at": TIMESTAMP,
        "ingested_at": TIMESTAMP,
    }


def test_enrich_comment_topics_counts_each_topic_once_per_comment():
    comment = make_comment(
        "comment-1",
        "VOCAL vocal ＶＯＣＡＬ dance DANCE visual visual",
    )

    records = enrich_comment_topics(comment, TOPICS)

    assert [record["topic_id"] for record in records] == [
        "vocal",
        "dance",
        "visual",
    ]
    assert [record["topic_count"] for record in records] == [1, 1, 1]
    assert [record["matched_keywords"] for record in records] == [
        ("vocal",),
        ("dance",),
        ("visual",),
    ]
    assert all(
        record["dictionary_version"] == "comment_topics_v1"
        for record in records
    )


def test_enrich_comment_topics_uses_ascii_word_boundaries():
    comment = make_comment(
        "comment-1",
        "vocals dancer visualization are not exact topic keywords",
    )

    assert enrich_comment_topics(comment, TOPICS) == []


def test_enrich_comment_topics_matches_chinese_and_korean_keywords():
    comment = make_comment(
        "comment-1",
        "唱功和보컬很強，舞蹈與안무也很棒，顏值和비주얼都突出",
    )

    records = enrich_comment_topics(comment, TOPICS)

    assert {
        record["topic_id"]: record["matched_keywords"]
        for record in records
    } == {
        "vocal": ("唱功", "보컬"),
        "dance": ("舞蹈", "안무"),
        "visual": ("顏值", "비주얼"),
    }
    assert all(record["topic_count"] == 1 for record in records)


def test_enrich_comment_dataset_topics_flattens_in_comment_order():
    comments = [
        make_comment("comment-1", "dance"),
        make_comment("comment-2", "vocal and visual"),
        make_comment("comment-3", "No configured topic"),
    ]

    records = enrich_comment_dataset_topics(comments, TOPICS)

    assert [record["comment_id"] for record in records] == [
        "comment-1",
        "comment-2",
        "comment-2",
    ]
    assert [record["topic_id"] for record in records] == [
        "dance",
        "vocal",
        "visual",
    ]


def test_enrich_comment_topics_preserves_original_comment():
    comment = make_comment("comment-1", "vocal")

    enrich_comment_topics(comment, TOPICS)

    assert comment["comment_text"] == "vocal"
    assert "topics" not in comment


def test_enrich_comment_topics_rejects_non_string_comment_text():
    comment = make_comment("comment-1", "vocal")
    comment["comment_text"] = None

    with pytest.raises(ValueError, match="comment_text must be a string"):
        enrich_comment_topics(comment, TOPICS)
