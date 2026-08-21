import json
from datetime import datetime, timezone

from storage.raw_video_writer import write_raw_video_metadata


def test_write_raw_video_metadata_preserves_response_and_lineage(tmp_path):
    raw_response = {
        "items": [
            {
                "id": "video-1",
                "snippet": {"title": "測試影片"},
                "statistics": {
                    "viewCount": "100",
                    "likeCount": "20",
                    "commentCount": "5",
                },
            }
        ]
    }
    ingested_at = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)

    output_path = write_raw_video_metadata(
        raw_response=raw_response,
        video_id="video-1",
        ingested_at=ingested_at,
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path
        / "video-1"
        / "2026-08-21"
        / "20260821T093000000000Z_video.json"
    )

    with output_path.open(encoding="utf-8") as output_file:
        saved_document = json.load(output_file)

    assert saved_document == {
        "video_id": "video-1",
        "ingested_at": "2026-08-21T09:30:00+00:00",
        "raw_response": raw_response,
    }
