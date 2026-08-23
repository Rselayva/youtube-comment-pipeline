import logging
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

import main as pipeline_main
from storage.pipeline_storage import DEFAULT_PIPELINE_STORAGE
from video_input import PipelineArguments


VIDEO_ID = "aFrQIJ5cbRc"
MAX_PAGES = 2
PAGE_SIZE = 10


@patch("main.write_run_manifest")
@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_runs_ingestion_read_and_transformation_in_order(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    mock_write_run_manifest,
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
        "video_topic_metrics_records": 3,
        "daily_topic_metrics_records": 6,
        "video_topic_metrics_output_path": Path("video_topics.jsonl"),
        "daily_topic_metrics_output_path": Path("daily_topics.jsonl"),
    }
    mock_write_run_manifest.return_value = Path("run.json")

    with caplog.at_level(logging.INFO):
        result = pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_ingest_comment_pages.assert_called_once_with(
        video_id=VIDEO_ID,
        max_pages=MAX_PAGES,
        page_size=PAGE_SIZE,
        ingested_at=ANY,
        raw_comments_dir=DEFAULT_PIPELINE_STORAGE.raw_comments_dir,
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
        raw_videos_dir=DEFAULT_PIPELINE_STORAGE.raw_videos_dir,
    )
    mock_read_raw_comment_pages.assert_called_once_with(raw_paths)
    mock_process_comment_pages.assert_called_once_with(
        raw_documents,
        silver_base_dir=DEFAULT_PIPELINE_STORAGE.silver_comments_dir,
        rejected_base_dir=(
            DEFAULT_PIPELINE_STORAGE.rejected_comments_dir
        ),
        mention_base_dir=DEFAULT_PIPELINE_STORAGE.silver_mentions_dir,
        topic_base_dir=DEFAULT_PIPELINE_STORAGE.silver_topics_dir,
        video_sov_base_dir=(
            DEFAULT_PIPELINE_STORAGE.gold_video_entity_sov_dir
        ),
        daily_sov_base_dir=(
            DEFAULT_PIPELINE_STORAGE.gold_daily_entity_sov_dir
        ),
        video_topic_metrics_base_dir=(
            DEFAULT_PIPELINE_STORAGE.gold_video_topic_metrics_dir
        ),
        daily_topic_metrics_base_dir=(
            DEFAULT_PIPELINE_STORAGE.gold_daily_topic_metrics_dir
        ),
    )
    mock_write_run_manifest.assert_called_once()
    assert mock_write_run_manifest.call_args.kwargs == {
        "base_dir": DEFAULT_PIPELINE_STORAGE.run_manifests_dir,
    }
    run_manifest = mock_write_run_manifest.call_args.args[0]
    assert run_manifest["schema_version"] == 1
    assert run_manifest["status"] == "succeeded"
    assert run_manifest["video_id"] == VIDEO_ID
    assert run_manifest["parameters"] == {
        "max_pages": MAX_PAGES,
        "page_size": PAGE_SIZE,
    }
    assert run_manifest["dictionary_versions"] == {
        "entity": "nmixx_v2",
        "topic": "comment_topics_v1",
    }
    assert run_manifest["counts"]["raw_comment_pages"] == 2
    assert run_manifest["counts"]["entity_mention_records"] == 2
    assert run_manifest["counts"]["video_topic_metrics_records"] == 3
    assert run_manifest["artifacts"]["raw_video_metadata"] == Path(
        "video.json"
    )
    assert run_manifest["artifacts"]["raw_comment_pages"] == raw_paths
    assert run_manifest["artifacts"]["silver_comments"] == Path(
        "silver.jsonl"
    )
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
    assert "video_topic_metrics_records=3" in caplog.text
    assert "daily_topic_metrics_records=6" in caplog.text
    assert "video_topic_metrics_output_path=video_topics.jsonl" in caplog.text
    assert "daily_topic_metrics_output_path=daily_topics.jsonl" in caplog.text
    assert "run_manifest_complete" in caplog.text
    assert "output_path=run.json" in caplog.text
    assert result == Path("run.json")


@patch("main.write_run_manifest")
@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_logs_and_reraises_downstream_failure(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    mock_write_run_manifest,
    caplog,
):
    mock_ingest_video_metadata.return_value = Path("video.json")
    mock_ingest_comment_pages.return_value = [Path("page_0001.json")]
    mock_read_raw_comment_pages.side_effect = ValueError(
        "invalid raw document"
    )
    mock_write_run_manifest.return_value = Path("failed_run.json")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="invalid raw document"):
            pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_process_comment_pages.assert_not_called()
    mock_write_run_manifest.assert_called_once()
    failed_manifest = mock_write_run_manifest.call_args.args[0]
    assert failed_manifest["status"] == "failed"
    assert failed_manifest["failure"] == {
        "stage": "raw_comment_read",
        "error_type": "ValueError",
    }
    assert "message" not in failed_manifest["failure"]
    assert failed_manifest["artifacts"]["raw_video_metadata"] == Path(
        "video.json"
    )
    assert failed_manifest["artifacts"]["raw_comment_pages"] == [
        Path("page_0001.json")
    ]
    assert "pipeline_failed" in caplog.text
    assert "error_type=ValueError" in caplog.text


@patch("main.write_run_manifest")
@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_stops_before_comments_when_video_metadata_fails(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    mock_write_run_manifest,
):
    mock_ingest_video_metadata.side_effect = ValueError("metadata failed")
    mock_write_run_manifest.return_value = Path("failed_run.json")

    with pytest.raises(ValueError, match="metadata failed"):
        pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_ingest_comment_pages.assert_not_called()
    mock_read_raw_comment_pages.assert_not_called()
    mock_process_comment_pages.assert_not_called()
    failed_manifest = mock_write_run_manifest.call_args.args[0]
    assert failed_manifest["failure"] == {
        "stage": "video_metadata_ingestion",
        "error_type": "ValueError",
    }
    assert failed_manifest["counts"] == {"raw_comment_pages": 0}
    assert failed_manifest["artifacts"] == {
        "raw_video_metadata": None,
        "raw_comment_pages": [],
    }


@patch("main.write_run_manifest")
@patch("main.process_comment_pages")
@patch("main.read_raw_comment_pages")
@patch("main.ingest_comment_pages")
@patch("main.ingest_video_metadata")
def test_main_preserves_original_error_when_failure_manifest_write_fails(
    mock_ingest_video_metadata,
    mock_ingest_comment_pages,
    mock_read_raw_comment_pages,
    mock_process_comment_pages,
    mock_write_run_manifest,
    caplog,
):
    mock_ingest_video_metadata.return_value = Path("video.json")
    mock_ingest_comment_pages.return_value = [Path("page_0001.json")]
    mock_read_raw_comment_pages.side_effect = ValueError(
        "original pipeline failure"
    )
    mock_write_run_manifest.side_effect = OSError(
        "manifest storage unavailable"
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="original pipeline failure"):
            pipeline_main.main(VIDEO_ID, MAX_PAGES, PAGE_SIZE)

    mock_process_comment_pages.assert_not_called()
    assert mock_write_run_manifest.call_count == 1
    assert "failure_manifest_write_failed" in caplog.text
    assert "original_error_type=ValueError" in caplog.text
    assert "manifest_error_type=OSError" in caplog.text


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
