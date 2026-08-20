from pathlib import Path

from storage.rejected_writer import (
    DEFAULT_REJECTED_COMMENTS_DIR,
    write_rejected_comments,
)
from storage.silver_writer import (
    DEFAULT_SILVER_COMMENTS_DIR,
    write_silver_comments,
)
from transformation.comment_parser import (
    parse_comment_page,
    parse_utc_timestamp,
)
from validation.comment_validator import validate_comment_dataset


def process_comment_pages(
    raw_documents: list[dict],
    silver_base_dir: Path = DEFAULT_SILVER_COMMENTS_DIR,
    rejected_base_dir: Path = DEFAULT_REJECTED_COMMENTS_DIR,
) -> dict:
    if not raw_documents:
        raise ValueError("At least one raw document is required")

    video_ids = {document["video_id"] for document in raw_documents}
    ingested_at_values = {
        document["ingested_at"] for document in raw_documents
    }

    if len(video_ids) != 1:
        raise ValueError("Raw documents must have the same video_id")

    if len(ingested_at_values) != 1:
        raise ValueError("Raw documents must have the same ingested_at")

    video_id = next(iter(video_ids))
    ingested_at = parse_utc_timestamp(next(iter(ingested_at_values)))
    parsed_comments = [
        comment
        for raw_document in raw_documents
        for comment in parse_comment_page(raw_document)
    ]
    valid_records, rejected_records = validate_comment_dataset(
        parsed_comments
    )

    silver_output_path = None
    if valid_records:
        silver_output_path = write_silver_comments(
            comments=valid_records,
            video_id=video_id,
            ingested_at=ingested_at,
            base_dir=silver_base_dir,
        )

    rejected_output_path = None
    if rejected_records:
        rejected_output_path = write_rejected_comments(
            comments=rejected_records,
            video_id=video_id,
            ingested_at=ingested_at,
            base_dir=rejected_base_dir,
        )

    return {
        "records_parsed": len(parsed_comments),
        "valid_records": len(valid_records),
        "rejected_records": len(rejected_records),
        "silver_output_path": silver_output_path,
        "rejected_output_path": rejected_output_path,
    }
