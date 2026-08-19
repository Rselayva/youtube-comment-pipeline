import json
from datetime import datetime, timezone

from storage.raw_writer import write_raw_comment_page


def test_write_raw_comment_page_preserves_response_and_metadata(tmp_path):
    raw_response = {
        "items": [
            {
                "id": "comment-1",
                "text": "測試留言",
            }
        ]
    }
    ingested_at = datetime(2026, 8, 18, 9, 30, tzinfo=timezone.utc)

    output_path = write_raw_comment_page(
        raw_response=raw_response,
        video_id="test-video-id",
        page_number=1,
        ingested_at=ingested_at,
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path
        / "test-video-id"
        / "2026-08-18"
        / "20260818T093000000000Z_page_0001.json"
    )

    with output_path.open(encoding="utf-8") as output_file:
        saved_document = json.load(output_file)

    assert saved_document == {
        "video_id": "test-video-id",
        "page_number": 1,
        "ingested_at": "2026-08-18T09:30:00+00:00",
        "raw_response": raw_response,
    }
