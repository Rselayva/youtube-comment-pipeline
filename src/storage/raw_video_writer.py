import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RAW_VIDEOS_DIR = Path("data/raw/youtube/videos")


def write_raw_video_metadata(
    raw_response: dict,
    video_id: str,
    ingested_at: datetime,
    base_dir: Path = DEFAULT_RAW_VIDEOS_DIR,
) -> Path:
    ingested_at_utc = ingested_at.astimezone(timezone.utc)
    ingestion_date = ingested_at_utc.strftime("%Y-%m-%d")
    ingestion_timestamp = ingested_at_utc.strftime("%Y%m%dT%H%M%S%fZ")

    output_dir = base_dir / video_id / ingestion_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{ingestion_timestamp}_video.json"
    raw_document = {
        "video_id": video_id,
        "ingested_at": ingested_at_utc.isoformat(),
        "raw_response": raw_response,
    }

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(raw_document, output_file, ensure_ascii=False, indent=2)

    return output_path
