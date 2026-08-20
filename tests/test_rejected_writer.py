import json
from datetime import datetime, timedelta, timezone

from storage.rejected_writer import write_rejected_comments


def test_write_rejected_comments_preserves_errors_and_invalid_values(
    tmp_path,
):
    ingested_at = datetime(2026, 8, 20, 9, 30, tzinfo=timezone.utc)
    rejected_comment = {
        "comment_id": "comment-1",
        "video_id": "video-1",
        "comment_text": "測試留言",
        "like_count": -1,
        "published_at": "invalid timestamp",
        "updated_at": datetime(
            2026,
            8,
            20,
            16,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        "ingested_at": ingested_at,
        "validation_errors": [
            "like_count must be non-negative",
            "published_at must be a datetime",
        ],
    }

    output_path = write_rejected_comments(
        comments=[rejected_comment],
        video_id="video-1",
        ingested_at=ingested_at,
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path
        / "video-1"
        / "2026-08-20"
        / "20260820T093000000000Z_rejected.jsonl"
    )

    with output_path.open(encoding="utf-8") as output_file:
        saved_comment = json.loads(output_file.readline())

    assert saved_comment == {
        **rejected_comment,
        "published_at": "invalid timestamp",
        "updated_at": "2026-08-20T08:00:00+00:00",
        "ingested_at": "2026-08-20T09:30:00+00:00",
    }


def test_write_rejected_comments_handles_missing_timestamps(tmp_path):
    ingested_at = datetime(2026, 8, 20, 9, 30, tzinfo=timezone.utc)
    rejected_comment = {
        "comment_id": None,
        "updated_at": datetime(2026, 8, 20, 8, 0),
        "validation_errors": [
            "comment_id is required",
            "published_at is required",
            "updated_at must include timezone information",
        ],
    }

    output_path = write_rejected_comments(
        comments=[rejected_comment],
        video_id="video-1",
        ingested_at=ingested_at,
        base_dir=tmp_path,
    )

    with output_path.open(encoding="utf-8") as output_file:
        saved_comment = json.loads(output_file.readline())

    assert saved_comment["updated_at"] == "2026-08-20T08:00:00"
    assert "published_at" not in rejected_comment
    assert isinstance(rejected_comment["updated_at"], datetime)
