import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REJECTED_COMMENTS_DIR = Path("data/rejected/youtube/comments")


def serialize_rejected_comment(comment: dict) -> dict:
    serialized_comment = comment.copy()

    for field_name in ("published_at", "updated_at", "ingested_at"):
        field_value = serialized_comment.get(field_name)

        if isinstance(field_value, datetime):
            if field_value.tzinfo is None or field_value.utcoffset() is None:
                serialized_comment[field_name] = field_value.isoformat()
            else:
                serialized_comment[field_name] = field_value.astimezone(
                    timezone.utc
                ).isoformat()

    return serialized_comment


def write_rejected_comments(
    comments: list[dict],
    video_id: str,
    ingested_at: datetime,
    base_dir: Path = DEFAULT_REJECTED_COMMENTS_DIR,
) -> Path:
    ingested_at_utc = ingested_at.astimezone(timezone.utc)
    ingestion_date = ingested_at_utc.strftime("%Y-%m-%d")
    ingestion_timestamp = ingested_at_utc.strftime("%Y%m%dT%H%M%S%fZ")

    output_dir = base_dir / video_id / ingestion_date
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{ingestion_timestamp}_rejected.jsonl"

    with output_path.open("w", encoding="utf-8") as output_file:
        for comment in comments:
            serialized_comment = serialize_rejected_comment(comment)
            json.dump(serialized_comment, output_file, ensure_ascii=False)
            output_file.write("\n")

    return output_path
