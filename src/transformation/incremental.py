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
    merged_comments = select_latest_comment_versions(
        existing_comments + incoming_comments
    )

    return {
        "existing_records": len(existing_comments),
        "incoming_records": len(incoming_comments),
        "merged_records": len(merged_comments),
        "merged_comments": merged_comments,
    }
