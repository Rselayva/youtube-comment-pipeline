import json
from pathlib import Path

from storage.silver_writer import DEFAULT_SILVER_COMMENTS_DIR
from transformation.comment_parser import parse_utc_timestamp


TIMESTAMP_FIELDS = (
    "published_at",
    "updated_at",
    "ingested_at",
)


def list_silver_comment_files(
    video_id: str,
    base_dir: Path = DEFAULT_SILVER_COMMENTS_DIR,
) -> list[Path]:
    video_dir = base_dir / video_id

    if not video_dir.exists():
        return []

    return sorted(video_dir.glob("*/*_comments.jsonl"))


def deserialize_silver_comment(serialized_comment: dict) -> dict:
    comment = serialized_comment.copy()

    for field_name in TIMESTAMP_FIELDS:
        comment[field_name] = parse_utc_timestamp(comment[field_name])

    return comment


def read_silver_comments(paths: list[Path]) -> list[dict]:
    comments = []

    for path in paths:
        with path.open(encoding="utf-8") as input_file:
            for line in input_file:
                serialized_comment = json.loads(line)
                comments.append(
                    deserialize_silver_comment(serialized_comment)
                )

    return comments
