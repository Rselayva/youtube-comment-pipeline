from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import call, patch

import pytest

from transformation.pipeline import process_comment_pages


RAW_DOCUMENTS = [
    {
        "video_id": "video-1",
        "page_number": 1,
        "ingested_at": "2026-08-20T09:30:00+00:00",
        "raw_response": {"items": [{"id": "thread-1"}]},
    },
    {
        "video_id": "video-1",
        "page_number": 2,
        "ingested_at": "2026-08-20T09:30:00+00:00",
        "raw_response": {"items": [{"id": "thread-2"}]},
    },
]


@patch("transformation.pipeline.write_rejected_comments")
@patch("transformation.pipeline.write_silver_comments")
@patch("transformation.pipeline.prepare_incremental_comments")
@patch("transformation.pipeline.validate_comment_dataset")
@patch("transformation.pipeline.parse_comment_page")
def test_process_comment_pages_aggregates_and_writes_each_dataset_once(
    mock_parse_comment_page,
    mock_validate_comment_dataset,
    mock_prepare_incremental_comments,
    mock_write_silver_comments,
    mock_write_rejected_comments,
    tmp_path,
):
    first_comment = {"comment_id": "comment-1"}
    second_comment = {"comment_id": "comment-2"}
    rejected_comment = {
        "comment_id": "comment-2",
        "validation_errors": ["test error"],
    }
    mock_parse_comment_page.side_effect = [
        [first_comment],
        [second_comment],
    ]
    mock_validate_comment_dataset.return_value = (
        [first_comment],
        [rejected_comment],
    )
    mock_prepare_incremental_comments.return_value = {
        "existing_records": 3,
        "merged_records": 4,
        "records_to_write": [first_comment],
    }
    mock_write_silver_comments.return_value = Path("silver.jsonl")
    mock_write_rejected_comments.return_value = Path("rejected.jsonl")

    result = process_comment_pages(
        raw_documents=RAW_DOCUMENTS,
        silver_base_dir=tmp_path / "silver",
        rejected_base_dir=tmp_path / "rejected",
    )

    assert mock_parse_comment_page.call_args_list == [
        call(RAW_DOCUMENTS[0]),
        call(RAW_DOCUMENTS[1]),
    ]
    mock_validate_comment_dataset.assert_called_once_with(
        [first_comment, second_comment]
    )
    mock_prepare_incremental_comments.assert_called_once_with(
        incoming_comments=[first_comment],
        video_id="video-1",
        silver_base_dir=tmp_path / "silver",
    )
    mock_write_silver_comments.assert_called_once_with(
        comments=[first_comment],
        video_id="video-1",
        ingested_at=datetime(
            2026,
            8,
            20,
            9,
            30,
            tzinfo=timezone.utc,
        ),
        base_dir=tmp_path / "silver",
    )
    mock_write_rejected_comments.assert_called_once_with(
        comments=[rejected_comment],
        video_id="video-1",
        ingested_at=datetime(
            2026,
            8,
            20,
            9,
            30,
            tzinfo=timezone.utc,
        ),
        base_dir=tmp_path / "rejected",
    )
    assert result == {
        "records_parsed": 2,
        "valid_records": 1,
        "rejected_records": 1,
        "existing_silver_records": 3,
        "merged_silver_records": 4,
        "silver_records_written": 1,
        "silver_output_path": Path("silver.jsonl"),
        "rejected_output_path": Path("rejected.jsonl"),
    }


@patch("transformation.pipeline.write_rejected_comments")
@patch("transformation.pipeline.write_silver_comments")
@patch("transformation.pipeline.prepare_incremental_comments")
@patch("transformation.pipeline.validate_comment_dataset")
@patch("transformation.pipeline.parse_comment_page")
def test_process_comment_pages_skips_empty_output_datasets(
    mock_parse_comment_page,
    mock_validate_comment_dataset,
    mock_prepare_incremental_comments,
    mock_write_silver_comments,
    mock_write_rejected_comments,
):
    mock_parse_comment_page.return_value = []
    mock_validate_comment_dataset.return_value = ([], [])

    result = process_comment_pages([RAW_DOCUMENTS[0]])

    mock_write_silver_comments.assert_not_called()
    mock_write_rejected_comments.assert_not_called()
    mock_prepare_incremental_comments.assert_not_called()
    assert result["silver_records_written"] == 0
    assert result["silver_output_path"] is None
    assert result["rejected_output_path"] is None


@patch("transformation.pipeline.write_rejected_comments")
@patch("transformation.pipeline.write_silver_comments")
@patch("transformation.pipeline.prepare_incremental_comments")
@patch("transformation.pipeline.validate_comment_dataset")
@patch("transformation.pipeline.parse_comment_page")
def test_process_comment_pages_skips_unchanged_silver_records(
    mock_parse_comment_page,
    mock_validate_comment_dataset,
    mock_prepare_incremental_comments,
    mock_write_silver_comments,
    mock_write_rejected_comments,
):
    unchanged_comment = {"comment_id": "comment-1"}
    mock_parse_comment_page.return_value = [unchanged_comment]
    mock_validate_comment_dataset.return_value = ([unchanged_comment], [])
    mock_prepare_incremental_comments.return_value = {
        "existing_records": 1,
        "merged_records": 1,
        "records_to_write": [],
    }

    result = process_comment_pages([RAW_DOCUMENTS[0]])

    mock_write_silver_comments.assert_not_called()
    mock_write_rejected_comments.assert_not_called()
    assert result["silver_records_written"] == 0
    assert result["silver_output_path"] is None


def test_process_comment_pages_rejects_empty_batch():
    with pytest.raises(
        ValueError,
        match="At least one raw document is required",
    ):
        process_comment_pages([])


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_error"),
    [
        (
            "video_id",
            "video-2",
            "Raw documents must have the same video_id",
        ),
        (
            "ingested_at",
            "2026-08-20T10:30:00+00:00",
            "Raw documents must have the same ingested_at",
        ),
    ],
)
def test_process_comment_pages_rejects_mixed_batch_metadata(
    field_name,
    invalid_value,
    expected_error,
):
    raw_documents = [document.copy() for document in RAW_DOCUMENTS]
    raw_documents[1][field_name] = invalid_value

    with pytest.raises(ValueError, match=expected_error):
        process_comment_pages(raw_documents)


def test_process_comment_pages_is_idempotent_for_unchanged_reingestion(
    tmp_path,
):
    raw_document = {
        "video_id": "video-1",
        "page_number": 1,
        "ingested_at": "2026-08-20T09:30:00+00:00",
        "raw_response": {
            "items": [
                {
                    "snippet": {
                        "totalReplyCount": 0,
                        "topLevelComment": {
                            "id": "comment-1",
                            "snippet": {
                                "videoId": "video-1",
                                "authorDisplayName": "Test Author",
                                "textOriginal": "Unchanged comment",
                                "likeCount": 1,
                                "publishedAt": "2026-08-19T08:00:00Z",
                                "updatedAt": "2026-08-19T08:00:00Z",
                            },
                        },
                    },
                }
            ]
        },
    }
    silver_dir = tmp_path / "silver"
    rejected_dir = tmp_path / "rejected"

    first_result = process_comment_pages(
        [raw_document],
        silver_base_dir=silver_dir,
        rejected_base_dir=rejected_dir,
    )
    reingested_document = raw_document.copy()
    reingested_document["ingested_at"] = "2026-08-20T10:30:00+00:00"
    second_result = process_comment_pages(
        [reingested_document],
        silver_base_dir=silver_dir,
        rejected_base_dir=rejected_dir,
    )

    assert first_result["silver_records_written"] == 1
    assert first_result["silver_output_path"].exists()
    assert second_result["existing_silver_records"] == 1
    assert second_result["silver_records_written"] == 0
    assert second_result["silver_output_path"] is None
    assert len(list(silver_dir.rglob("*_comments.jsonl"))) == 1
