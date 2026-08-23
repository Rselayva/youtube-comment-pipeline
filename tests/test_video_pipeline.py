from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ingestion.video_pipeline import ingest_video_metadata
from storage.raw_video_writer import DEFAULT_RAW_VIDEOS_DIR


@patch("ingestion.video_pipeline.write_raw_video_metadata")
@patch("ingestion.video_pipeline.get_video_metadata")
def test_ingest_video_metadata_fetches_and_writes_raw_response(
    mock_get_video_metadata,
    mock_write_raw_video_metadata,
):
    ingested_at = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)
    raw_response = {"items": [{"id": "video-1"}]}
    output_path = Path("video.json")
    mock_get_video_metadata.return_value = raw_response
    mock_write_raw_video_metadata.return_value = output_path

    result = ingest_video_metadata(
        video_id="video-1",
        ingested_at=ingested_at,
    )

    assert result == output_path
    mock_get_video_metadata.assert_called_once_with("video-1")
    mock_write_raw_video_metadata.assert_called_once_with(
        raw_response=raw_response,
        video_id="video-1",
        ingested_at=ingested_at,
        base_dir=DEFAULT_RAW_VIDEOS_DIR,
    )
