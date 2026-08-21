import json
from datetime import timezone
from pathlib import Path


DEFAULT_SILVER_TOPICS_DIR = Path(
    "data/silver/youtube/comment_topics"
)


def serialize_topic_record(topic_record: dict) -> dict:
    serialized_record = topic_record.copy()

    for field_name in ("published_at", "ingested_at"):
        field_value = serialized_record[field_name]
        serialized_record[field_name] = field_value.astimezone(
            timezone.utc
        ).isoformat()

    serialized_record["matched_keywords"] = list(
        serialized_record["matched_keywords"]
    )
    return serialized_record


def write_topic_snapshot(
    topic_records: list[dict],
    video_id: str,
    dictionary_version: str,
    base_dir: Path = DEFAULT_SILVER_TOPICS_DIR,
) -> Path:
    output_dir = base_dir / dictionary_version / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "current_topics.jsonl"
    temporary_path = output_dir / ".current_topics.jsonl.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as output_file:
            for topic_record in topic_records:
                json.dump(
                    serialize_topic_record(topic_record),
                    output_file,
                    ensure_ascii=False,
                )
                output_file.write("\n")

        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path
