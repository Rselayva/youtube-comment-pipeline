import json
from datetime import datetime, timedelta, timezone

import pytest

from storage.topic_writer import write_topic_snapshot


def make_topic_record() -> dict:
    return {
        "comment_id": "comment-1",
        "video_id": "video-1",
        "topic_id": "vocal",
        "display_name": "Vocal",
        "matched_keywords": ("唱功", "보컬"),
        "topic_count": 1,
        "published_at": datetime(
            2026,
            8,
            21,
            17,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        "ingested_at": datetime(
            2026,
            8,
            21,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        "dictionary_version": "comment_topics_v1",
    }


def test_write_topic_snapshot_writes_versioned_current_snapshot(tmp_path):
    topic_record = make_topic_record()

    output_path = write_topic_snapshot(
        topic_records=[topic_record],
        video_id="video-1",
        dictionary_version="comment_topics_v1",
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path
        / "comment_topics_v1"
        / "video-1"
        / "current_topics.jsonl"
    )
    saved_record = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_record == {
        **topic_record,
        "matched_keywords": ["唱功", "보컬"],
        "published_at": "2026-08-21T09:00:00+00:00",
        "ingested_at": "2026-08-21T10:00:00+00:00",
    }


def test_write_topic_snapshot_replaces_previous_content(tmp_path):
    first_record = make_topic_record()
    output_path = write_topic_snapshot(
        [first_record],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )
    second_record = {
        **first_record,
        "topic_id": "dance",
        "display_name": "Dance",
        "matched_keywords": ("舞蹈",),
    }

    replaced_path = write_topic_snapshot(
        [second_record],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )

    assert replaced_path == output_path
    saved_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(saved_lines) == 1
    assert json.loads(saved_lines[0])["topic_id"] == "dance"


def test_write_topic_snapshot_can_clear_previous_snapshot(tmp_path):
    output_path = write_topic_snapshot(
        [make_topic_record()],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )

    write_topic_snapshot(
        [],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )

    assert output_path.read_text(encoding="utf-8") == ""


def test_write_topic_snapshot_does_not_mutate_input(tmp_path):
    topic_record = make_topic_record()

    write_topic_snapshot(
        [topic_record],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )

    assert topic_record["matched_keywords"] == ("唱功", "보컬")
    assert isinstance(topic_record["published_at"], datetime)


def test_write_topic_snapshot_removes_partial_file_on_failure(tmp_path):
    invalid_record = make_topic_record()
    del invalid_record["ingested_at"]

    with pytest.raises(KeyError, match="ingested_at"):
        write_topic_snapshot(
            [invalid_record],
            "video-1",
            "comment_topics_v1",
            tmp_path,
        )

    output_dir = tmp_path / "comment_topics_v1" / "video-1"
    assert list(output_dir.iterdir()) == []
