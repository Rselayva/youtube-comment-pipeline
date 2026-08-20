from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from transformation.incremental import prepare_incremental_comments


def make_comment(
    comment_id: str,
    comment_text: str,
    updated_hour: int,
    ingested_hour: int,
) -> dict:
    return {
        "comment_id": comment_id,
        "comment_text": comment_text,
        "updated_at": datetime(
            2026,
            8,
            20,
            updated_hour,
            tzinfo=timezone.utc,
        ),
        "ingested_at": datetime(
            2026,
            8,
            20,
            ingested_hour,
            tzinfo=timezone.utc,
        ),
    }


@patch("transformation.incremental.read_silver_comments")
@patch("transformation.incremental.list_silver_comment_files")
def test_prepare_incremental_comments_merges_existing_and_incoming_versions(
    mock_list_silver_comment_files,
    mock_read_silver_comments,
    tmp_path,
):
    existing_path = Path("existing.jsonl")
    existing_comment = make_comment(
        "comment-1",
        "Original text",
        updated_hour=8,
        ingested_hour=9,
    )
    updated_comment = make_comment(
        "comment-1",
        "Edited text",
        updated_hour=10,
        ingested_hour=11,
    )
    new_comment = make_comment(
        "comment-2",
        "New comment",
        updated_hour=9,
        ingested_hour=11,
    )
    mock_list_silver_comment_files.return_value = [existing_path]
    mock_read_silver_comments.return_value = [existing_comment]

    result = prepare_incremental_comments(
        incoming_comments=[updated_comment, new_comment],
        video_id="video-1",
        silver_base_dir=tmp_path,
    )

    mock_list_silver_comment_files.assert_called_once_with(
        video_id="video-1",
        base_dir=tmp_path,
    )
    mock_read_silver_comments.assert_called_once_with([existing_path])
    assert result == {
        "existing_records": 1,
        "incoming_records": 2,
        "merged_records": 2,
        "merged_comments": [updated_comment, new_comment],
    }


@patch("transformation.incremental.read_silver_comments")
@patch("transformation.incremental.list_silver_comment_files")
def test_prepare_incremental_comments_handles_first_load(
    mock_list_silver_comment_files,
    mock_read_silver_comments,
):
    incoming_comment = make_comment(
        "comment-1",
        "First load",
        updated_hour=8,
        ingested_hour=9,
    )
    mock_list_silver_comment_files.return_value = []
    mock_read_silver_comments.return_value = []

    result = prepare_incremental_comments(
        incoming_comments=[incoming_comment],
        video_id="video-1",
    )

    mock_read_silver_comments.assert_called_once_with([])
    assert result["existing_records"] == 0
    assert result["merged_comments"] == [incoming_comment]
