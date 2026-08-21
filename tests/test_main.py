import logging
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

import main as pipeline_main
from video_input import PipelineArguments


VIDEO_ID = "aFrQIJ5cbRc"
MAX_PAGES = 2
PAGE_SIZE = 10


@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_runs_ingestion_read_and_transformation_in_order(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    caplog,
):
    mock_ingest_video_metadata.return_value = Path("video.json")
    raw_paths = [Path("page_0001.json"), Path("page_0002.json")]
    raw_documents = [{"page_number": 1}, {"page_number": 2}]
    mock_ingest_comment_pages.return_value = raw_paths
    mock_read_raw_comment_pages.return_value = raw_documents
    mock_process_comment_pages.return_value = {
        "records_parsed": 2,
        "valid_records": 1,
        "rejected_records": 1,
        "existing_silver_records": 3,
        "merged_silver_records": 4,
        "silver_records_written": 1,
        "silver_output_path": Path("silver.jsonl"),
        "rejected_output_path": Path("rejected.jsonl"),
        "entity_dictionary_version": "nmixx_v2",
        "mention_records": 2,
        "group_mention_records": 1,
        "member_mention_records": 1,
        "mention_output_path": Path("mentions.jsonl"),
        "video_sov_records": 7,
        "daily_sov_records": 14,
        "video_sov_output_path": Path("video_sov.jsonl"),
        "daily_sov_output_path": Path("daily_sov.jsonl"),
        "topic_dictionary_version": "comment_topics_v1",
        "topic_records": 3,
        "topic_output_path": Path("topics.jsonl"),
    }

    with caplog.at_level(logging.INFO):
        pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_ingest_comment_pages.assert_called_once_with(
        video_id=VIDEO_ID,
        max_pages=MAX_PAGES,
        page_size=PAGE_SIZE,
        ingested_at=ANY,
    )
    video_ingested_at = mock_ingest_video_metadata.call_args.kwargs[
        "ingested_at"
    ]
    comment_ingested_at = mock_ingest_comment_pages.call_args.kwargs[
        "ingested_at"
    ]
    assert video_ingested_at is comment_ingested_at
    mock_ingest_video_metadata.assert_called_once_with(
        video_id=VIDEO_ID,
        ingested_at=ANY,
    )
    mock_read_raw_comment_pages.assert_called_once_with(raw_paths)
    mock_process_comment_pages.assert_called_once_with(raw_documents)
    assert "transformation_complete" in caplog.text
    assert "records_parsed=2" in caplog.text
    assert "valid_records=1" in caplog.text
    assert "rejected_records=1" in caplog.text
    assert "existing_silver_records=3" in caplog.text
    assert "merged_silver_records=4" in caplog.text
    assert "silver_records_written=1" in caplog.text
    assert "entity_dictionary_version=nmixx_v2" in caplog.text
    assert "mention_records=2" in caplog.text
    assert "group_mention_records=1" in caplog.text
    assert "member_mention_records=1" in caplog.text
    assert "mention_output_path=mentions.jsonl" in caplog.text
    assert "video_sov_records=7" in caplog.text
    assert "daily_sov_records=14" in caplog.text
    assert "video_sov_output_path=video_sov.jsonl" in caplog.text
    assert "daily_sov_output_path=daily_sov.jsonl" in caplog.text
    assert "topic_dictionary_version=comment_topics_v1" in caplog.text
    assert "topic_records=3" in caplog.text
    assert "topic_output_path=topics.jsonl" in caplog.text


@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_logs_and_reraises_downstream_failure(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    caplog,
):
    mock_ingest_video_metadata.return_value = Path("video.json")
    mock_ingest_comment_pages.return_value = [Path("page_0001.json")]
    mock_read_raw_comment_pages.side_effect = ValueError(
        "invalid raw document"
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="invalid raw document"):
            pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_process_comment_pages.assert_not_called()
    assert "pipeline_failed" in caplog.text
    assert "error_type=ValueError" in caplog.text


@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_stops_before_comments_when_video_metadata_fails(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
):
    mock_ingest_video_metadata.side_effect = ValueError("metadata failed")

    with pytest.raises(ValueError, match="metadata failed"):
        pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_ingest_comment_pages.assert_not_called()
    mock_read_raw_comment_pages.assert_not_called()
    mock_process_comment_pages.assert_not_called()


@patch("main.main")
@patch("main.parse_cli_args")
@patch("main.configure_logging")
def test_run_cli_configures_logging_parses_input_and_runs_pipeline(
    mock_configure_logging,
    mock_parse_cli_args,
    mock_main,
):
    mock_parse_cli_args.return_value = PipelineArguments(
        video_id=VIDEO_ID,
        max_pages=5,
        page_size=25,
    )

    pipeline_main.run_cli()

    mock_configure_logging.assert_called_once_with()
    mock_parse_cli_args.assert_called_once_with()
    mock_main.assert_called_once_with(
        video_id=VIDEO_ID,
        max_pages=5,
        page_size=25,
    )
