import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RAW_REPLIES_DIR = Path("data/raw/youtube/replies")


def write_raw_reply_page(
    raw_response: dict,
    video_id: str,
    parent_comment_id: str,
    page_number: int,
    ingested_at: datetime,
    base_dir: Path = DEFAULT_RAW_REPLIES_DIR,
) -> Path:
    ingested_at_utc = ingested_at.astimezone(timezone.utc)
    ingestion_date = ingested_at_utc.strftime("%Y-%m-%d")
    ingestion_timestamp = ingested_at_utc.strftime("%Y%m%dT%H%M%S%fZ")
    parent_id_hash = hashlib.sha256(
        parent_comment_id.encode("utf-8")
    ).hexdigest()[:16]

    output_dir = base_dir / video_id / ingestion_date
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / (
        f"{ingestion_timestamp}_parent_{parent_id_hash}_"
        f"page_{page_number:04d}.json"
    )
    raw_document = {
        "video_id": video_id,
        "parent_comment_id": parent_comment_id,
        "page_number": page_number,
        "ingested_at": ingested_at_utc.isoformat(),
        "raw_response": raw_response,
    }

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(raw_document, output_file, ensure_ascii=False, indent=2)

    return output_path
