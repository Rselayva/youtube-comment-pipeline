import json
from datetime import datetime, timedelta, timezone

import pytest

from storage.silver_writer import write_silver_comments


def test_write_silver_comments_writes_one_json_record_per_line(tmp_path):
    ingested_at = datetime(2026, 8, 19, 9, 30, tzinfo=timezone.utc)
    published_timezone = timezone(timedelta(hours=8))
    comments = [
        {
            "comment_id": "comment-1",
            "video_id": "video-1",
            "author_name": "Test author",
            "comment_text": "第一筆留言",
            "like_count": 1,
            "total_reply_count": 0,
            "published_at": datetime(
                2026,
                8,
                19,
                16,
                0,
                tzinfo=published_timezone,
            ),
            "updated_at": datetime(
                2026,
                8,
                19,
                8,
                30,
                tzinfo=timezone.utc,
            ),
            "ingested_at": ingested_at,
        },
        {
            "comment_id": "comment-2",
            "video_id": "video-1",
            "author_name": None,
            "comment_text": "Second comment",
            "like_count": 0,
            "total_reply_count": 1,
            "published_at": datetime(
                2026,
                8,
                19,
                7,
                0,
                tzinfo=timezone.utc,
            ),
            "updated_at": datetime(
                2026,
                8,
                19,
                7,
                0,
                tzinfo=timezone.utc,
            ),
            "ingested_at": ingested_at,
        },
    ]

    output_path = write_silver_comments(
        comments=comments,
        video_id="video-1",
        ingested_at=ingested_at,
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path
        / "video-1"
        / "2026-08-19"
        / "20260819T093000000000Z_comments.jsonl"
    )

    with output_path.open(encoding="utf-8") as output_file:
        saved_comments = [json.loads(line) for line in output_file]

    assert len(saved_comments) == 2
    assert saved_comments[0] == {
        **comments[0],
        "published_at": "2026-08-19T08:00:00+00:00",
        "updated_at": "2026-08-19T08:30:00+00:00",
        "ingested_at": "2026-08-19T09:30:00+00:00",
    }
    assert saved_comments[1]["comment_id"] == "comment-2"
    assert saved_comments[1]["author_name"] is None
    assert list(output_path.parent.iterdir()) == [output_path]


def test_write_silver_comments_does_not_mutate_input_records(tmp_path):
    timestamp = datetime(2026, 8, 19, 9, 30, tzinfo=timezone.utc)
    comment = {
        "published_at": timestamp,
        "updated_at": timestamp,
        "ingested_at": timestamp,
    }

    write_silver_comments(
        comments=[comment],
        video_id="video-1",
        ingested_at=timestamp,
        base_dir=tmp_path,
    )

    assert comment["published_at"] is timestamp
    assert comment["updated_at"] is timestamp
    assert comment["ingested_at"] is timestamp


def test_write_silver_comments_removes_partial_file_on_failure(tmp_path):
    timestamp = datetime(2026, 8, 20, 9, 30, tzinfo=timezone.utc)
    invalid_comment = {
        "published_at": timestamp,
        "updated_at": timestamp,
    }

    with pytest.raises(KeyError, match="ingested_at"):
        write_silver_comments(
            comments=[invalid_comment],
            video_id="video-1",
            ingested_at=timestamp,
            base_dir=tmp_path,
        )

    output_dir = tmp_path / "video-1" / "2026-08-20"
    assert list(output_dir.iterdir()) == []
