import json
from datetime import datetime, timezone

import pytest

from storage.silver_reader import read_silver_comments


def test_read_silver_comments_preserves_file_and_line_order(tmp_path):
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    first_comment = {
        "comment_id": "comment-1",
        "published_at": "2026-08-19T16:00:00+08:00",
        "updated_at": "2026-08-19T08:30:00+00:00",
        "ingested_at": "2026-08-20T09:30:00+00:00",
    }
    second_comment = {
        "comment_id": "comment-2",
        "published_at": "2026-08-19T07:00:00Z",
        "updated_at": "2026-08-19T07:00:00Z",
        "ingested_at": "2026-08-20T09:30:00Z",
    }

    with first_path.open("w", encoding="utf-8") as output_file:
        output_file.write(json.dumps(first_comment) + "\n")
        output_file.write(json.dumps(second_comment) + "\n")

    with second_path.open("w", encoding="utf-8") as output_file:
        output_file.write(json.dumps(first_comment) + "\n")

    comments = read_silver_comments([second_path, first_path])

    assert [comment["comment_id"] for comment in comments] == [
        "comment-1",
        "comment-1",
        "comment-2",
    ]
    assert comments[0]["published_at"] == datetime(
        2026,
        8,
        19,
        8,
        0,
        tzinfo=timezone.utc,
    )
    assert comments[2]["ingested_at"] == datetime(
        2026,
        8,
        20,
        9,
        30,
        tzinfo=timezone.utc,
    )


def test_read_silver_comments_rejects_timestamp_without_timezone(tmp_path):
    path = tmp_path / "invalid.jsonl"
    serialized_comment = {
        "comment_id": "comment-1",
        "published_at": "2026-08-19T08:00:00",
        "updated_at": "2026-08-19T08:30:00+00:00",
        "ingested_at": "2026-08-20T09:30:00+00:00",
    }
    path.write_text(json.dumps(serialized_comment) + "\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Timestamp must include timezone information",
    ):
        read_silver_comments([path])
