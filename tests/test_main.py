import logging
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

import main as pipeline_main


@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
def test_main_runs_ingestion_read_and_transformation_in_order(
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    caplog,
):
    raw_paths = [Path("page_0001.json"), Path("page_0002.json")]
    raw_documents = [{"page_number": 1}, {"page_number": 2}]
    mock_ingest_comment_pages.return_value = raw_paths
    mock_read_raw_comment_pages.return_value = raw_documents
    mock_process_comment_pages.return_value = {
        "records_parsed": 2,
        "valid_records": 1,
        "rejected_records": 1,
        "silver_output_path": Path("silver.jsonl"),
        "rejected_output_path": Path("rejected.jsonl"),
    }

    with caplog.at_level(logging.INFO):
        pipeline_main.main()

    mock_ingest_comment_pages.assert_called_once_with(
        video_id=pipeline_main.VIDEO_ID,
        max_pages=pipeline_main.MAX_PAGES,
        ingested_at=ANY,
    )
    mock_read_raw_comment_pages.assert_called_once_with(raw_paths)
    mock_process_comment_pages.assert_called_once_with(raw_documents)
    assert "transformation_complete" in caplog.text
    assert "records_parsed=2" in caplog.text
    assert "valid_records=1" in caplog.text
    assert "rejected_records=1" in caplog.text


@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
def test_main_logs_and_reraises_downstream_failure(
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    caplog,
):
    mock_ingest_comment_pages.return_value = [Path("page_0001.json")]
    mock_read_raw_comment_pages.side_effect = ValueError(
        "invalid raw document"
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="invalid raw document"):
            pipeline_main.main()

    mock_process_comment_pages.assert_not_called()
    assert "pipeline_failed" in caplog.text
    assert "error_type=ValueError" in caplog.text
