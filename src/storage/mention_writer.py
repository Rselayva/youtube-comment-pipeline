import json
from datetime import timezone
from pathlib import Path


DEFAULT_SILVER_MENTIONS_DIR = Path(
    "data/silver/youtube/comment_entity_mentions"
)


def serialize_mention_record(mention: dict) -> dict:
    serialized_mention = mention.copy()

    for field_name in ("published_at", "ingested_at"):
        field_value = serialized_mention[field_name]
        serialized_mention[field_name] = field_value.astimezone(
            timezone.utc
        ).isoformat()

    serialized_mention["matched_aliases"] = list(
        serialized_mention["matched_aliases"]
    )
    return serialized_mention


def write_mention_snapshot(
    mentions: list[dict],
    video_id: str,
    dictionary_version: str,
    base_dir: Path = DEFAULT_SILVER_MENTIONS_DIR,
) -> Path:
    output_dir = base_dir / dictionary_version / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "current_mentions.jsonl"
    temporary_path = output_dir / ".current_mentions.jsonl.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as output_file:
            for mention in mentions:
                serialized_mention = serialize_mention_record(mention)
                json.dump(
                    serialized_mention,
                    output_file,
                    ensure_ascii=False,
                )
                output_file.write("\n")

        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path
