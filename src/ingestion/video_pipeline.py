import logging
from datetime import datetime
from pathlib import Path

from ingestion.youtube_client import get_video_metadata
from storage.raw_video_writer import write_raw_video_metadata


logger = logging.getLogger(__name__)


def ingest_video_metadata(
    video_id: str,
    ingested_at: datetime,
) -> Path:
    raw_response = get_video_metadata(video_id)
    output_path = write_raw_video_metadata(
        raw_response=raw_response,
        video_id=video_id,
        ingested_at=ingested_at,
    )
    logger.info(
        "raw_video_metadata_written video_id=%s output_path=%s",
        video_id,
        output_path,
    )
    return output_path
