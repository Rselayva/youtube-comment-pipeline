import hashlib
import json
from datetime import datetime, timezone

from storage.raw_reply_writer import write_raw_reply_page


def test_write_raw_reply_page_preserves_response_and_lineage(tmp_path):
    raw_response = {
        "items": [
            {
                "id": "reply-1",
                "snippet": {"textOriginal": "回覆內容"},
            }
        ]
    }
    ingested_at = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)
    parent_comment_id = "parent/comment-with-unsafe-path"
    parent_id_hash = hashlib.sha256(
        parent_comment_id.encode("utf-8")
    ).hexdigest()[:16]

    output_path = write_raw_reply_page(
        raw_response=raw_response,
        video_id="video-1",
        parent_comment_id=parent_comment_id,
        page_number=2,
        ingested_at=ingested_at,
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path
        / "video-1"
        / "2026-08-21"
        / (
            f"20260821T093000000000Z_parent_{parent_id_hash}_"
            "page_0002.json"
        )
    )
    assert parent_comment_id not in output_path.name

    with output_path.open(encoding="utf-8") as output_file:
        saved_document = json.load(output_file)

    assert saved_document == {
        "video_id": "video-1",
        "parent_comment_id": parent_comment_id,
        "page_number": 2,
        "ingested_at": "2026-08-21T09:30:00+00:00",
        "raw_response": raw_response,
    }
