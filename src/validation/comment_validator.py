from collections import Counter
from datetime import datetime


REQUIRED_COMMENT_FIELDS = (
    "comment_id",
    "video_id",
    "comment_text",
    "published_at",
    "updated_at",
    "ingested_at",
    "like_count",
    "total_reply_count",
)

COUNT_FIELDS = (
    "like_count",
    "total_reply_count",
)

TIMESTAMP_FIELDS = (
    "published_at",
    "updated_at",
    "ingested_at",
)


def validate_comment_record(comment: dict) -> list[str]:
    validation_errors = []

    for field_name in REQUIRED_COMMENT_FIELDS:
        if field_name not in comment or comment[field_name] is None:
            validation_errors.append(f"{field_name} is required")

    for field_name in COUNT_FIELDS:
        field_value = comment.get(field_name)

        if field_value is None:
            continue

        if isinstance(field_value, bool) or not isinstance(field_value, int):
            validation_errors.append(f"{field_name} must be an integer")
        elif field_value < 0:
            validation_errors.append(f"{field_name} must be non-negative")

    valid_timestamps = {}

    for field_name in TIMESTAMP_FIELDS:
        field_value = comment.get(field_name)

        if field_value is None:
            continue

        if not isinstance(field_value, datetime):
            validation_errors.append(f"{field_name} must be a datetime")
            continue

        if field_value.tzinfo is None or field_value.utcoffset() is None:
            validation_errors.append(
                f"{field_name} must include timezone information"
            )
            continue

        valid_timestamps[field_name] = field_value

    if len(valid_timestamps) == len(TIMESTAMP_FIELDS):
        if valid_timestamps["published_at"] > valid_timestamps["updated_at"]:
            validation_errors.append(
                "published_at must not be after updated_at"
            )

        if valid_timestamps["updated_at"] > valid_timestamps["ingested_at"]:
            validation_errors.append(
                "updated_at must not be after ingested_at"
            )

    return validation_errors


def validate_comment_dataset(
    comments: list[dict],
) -> tuple[list[dict], list[dict]]:
    comment_id_counts = Counter(
        comment["comment_id"]
        for comment in comments
        if comment.get("comment_id") is not None
    )

    valid_records = []
    rejected_records = []

    for comment in comments:
        validation_errors = validate_comment_record(comment)
        comment_id = comment.get("comment_id")

        if (
            comment_id is not None
            and comment_id_counts[comment_id] > 1
        ):
            validation_errors.append(
                "comment_id must be unique within the batch"
            )

        if validation_errors:
            rejected_record = comment.copy()
            rejected_record["validation_errors"] = validation_errors
            rejected_records.append(rejected_record)
        else:
            valid_records.append(comment)

    return valid_records, rejected_records
