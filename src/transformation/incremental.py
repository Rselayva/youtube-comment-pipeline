from pathlib import Path

from storage.silver_reader import (
    list_silver_comment_files,
    read_silver_comments,
)
from storage.silver_writer import DEFAULT_SILVER_COMMENTS_DIR
from transformation.comment_deduplicator import (
    select_latest_comment_versions,
)


def prepare_incremental_comments(
    incoming_comments: list[dict],
    video_id: str,
    silver_base_dir: Path = DEFAULT_SILVER_COMMENTS_DIR,
) -> dict:
    existing_paths = list_silver_comment_files(
        video_id=video_id,
        base_dir=silver_base_dir,
    )
    existing_comments = read_silver_comments(existing_paths)
    existing_latest_comments = select_latest_comment_versions(
        existing_comments
    )
    merged_comments = select_latest_comment_versions(
        existing_latest_comments + incoming_comments
    )
    existing_comments_by_id = {
        comment["comment_id"]: comment
        for comment in existing_latest_comments
    }
    records_to_write = []

    for merged_comment in merged_comments:
        existing_comment = existing_comments_by_id.get(
            merged_comment["comment_id"]
        )

        if existing_comment is None:
            records_to_write.append(merged_comment)
            continue

        merged_version = (
            merged_comment["updated_at"],
            merged_comment["ingested_at"],
        )
        existing_version = (
            existing_comment["updated_at"],
            existing_comment["ingested_at"],
        )

        if merged_version > existing_version:
            records_to_write.append(merged_comment)

    return {
        "existing_records": len(existing_comments),
        "incoming_records": len(incoming_comments),
        "merged_records": len(merged_comments),
        "records_to_write": records_to_write,
        "merged_comments": merged_comments,
    }
