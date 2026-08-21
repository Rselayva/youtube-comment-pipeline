import json
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
@patch("transformation.pipeline.write_daily_entity_sov_snapshot")
@patch("transformation.pipeline.write_video_entity_sov_snapshot")
@patch("transformation.pipeline.build_daily_entity_sov_metrics")
@patch("transformation.pipeline.build_video_entity_sov_metrics")
@patch("transformation.pipeline.write_mention_snapshot")
@patch("transformation.pipeline.enrich_comment_dataset_mentions")
@patch("transformation.pipeline.load_entity_alias_dictionary")
@patch("transformation.pipeline.prepare_incremental_comments")
@patch("transformation.pipeline.validate_comment_dataset")
@patch("transformation.pipeline.parse_comment_page")
def test_process_comment_pages_aggregates_and_writes_each_dataset_once(
    mock_parse_comment_page,
    mock_validate_comment_dataset,
    mock_prepare_incremental_comments,
    mock_load_entity_alias_dictionary,
    mock_enrich_comment_dataset_mentions,
    mock_write_mention_snapshot,
    mock_build_video_entity_sov_metrics,
    mock_build_daily_entity_sov_metrics,
    mock_write_video_entity_sov_snapshot,
    mock_write_daily_entity_sov_snapshot,
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
        "merged_comments": [first_comment],
    }
    mock_load_entity_alias_dictionary.return_value.dictionary_version = (
        "nmixx_v2"
    )
    mention_records = [
        {"entity_type": "group"},
        {"entity_type": "member"},
    ]
    mock_enrich_comment_dataset_mentions.return_value = mention_records
    mock_write_mention_snapshot.return_value = Path("mentions.jsonl")
    video_sov_metrics = [{"grain": "video"}]
    daily_sov_metrics = [{"grain": "daily"}, {"grain": "daily"}]
    mock_build_video_entity_sov_metrics.return_value = video_sov_metrics
    mock_build_daily_entity_sov_metrics.return_value = daily_sov_metrics
    mock_write_video_entity_sov_snapshot.return_value = Path(
        "video_sov.jsonl"
    )
    mock_write_daily_entity_sov_snapshot.return_value = Path(
        "daily_sov.jsonl"
    )
    mock_write_silver_comments.return_value = Path("silver.jsonl")
    mock_write_rejected_comments.return_value = Path("rejected.jsonl")

    result = process_comment_pages(
        raw_documents=RAW_DOCUMENTS,
        silver_base_dir=tmp_path / "silver",
        rejected_base_dir=tmp_path / "rejected",
        mention_base_dir=tmp_path / "mentions",
        video_sov_base_dir=tmp_path / "video-sov",
        daily_sov_base_dir=tmp_path / "daily-sov",
        entity_aliases_path=tmp_path / "aliases.json",
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
    mock_enrich_comment_dataset_mentions.assert_called_once_with(
        [first_comment],
        mock_load_entity_alias_dictionary.return_value,
    )
    mock_load_entity_alias_dictionary.assert_called_once_with(
        tmp_path / "aliases.json"
    )
    mock_write_mention_snapshot.assert_called_once_with(
        mentions=mention_records,
        video_id="video-1",
        dictionary_version="nmixx_v2",
        base_dir=tmp_path / "mentions",
    )
    mock_build_video_entity_sov_metrics.assert_called_once_with(
        [first_comment],
        mention_records,
        mock_load_entity_alias_dictionary.return_value,
    )
    mock_build_daily_entity_sov_metrics.assert_called_once_with(
        [first_comment],
        mention_records,
        mock_load_entity_alias_dictionary.return_value,
    )
    mock_write_video_entity_sov_snapshot.assert_called_once_with(
        metrics=video_sov_metrics,
        video_id="video-1",
        dictionary_version="nmixx_v2",
        base_dir=tmp_path / "video-sov",
    )
    mock_write_daily_entity_sov_snapshot.assert_called_once_with(
        metrics=daily_sov_metrics,
        video_id="video-1",
        dictionary_version="nmixx_v2",
        base_dir=tmp_path / "daily-sov",
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
        "dictionary_version": "nmixx_v2",
        "mention_records": 2,
        "group_mention_records": 1,
        "member_mention_records": 1,
        "mention_output_path": Path("mentions.jsonl"),
        "video_sov_records": 1,
        "daily_sov_records": 2,
        "video_sov_output_path": Path("video_sov.jsonl"),
        "daily_sov_output_path": Path("daily_sov.jsonl"),
    }


@patch("transformation.pipeline.write_rejected_comments")
@patch("transformation.pipeline.write_silver_comments")
@patch("transformation.pipeline.write_daily_entity_sov_snapshot")
@patch("transformation.pipeline.write_video_entity_sov_snapshot")
@patch("transformation.pipeline.build_daily_entity_sov_metrics")
@patch("transformation.pipeline.build_video_entity_sov_metrics")
@patch("transformation.pipeline.write_mention_snapshot")
@patch("transformation.pipeline.enrich_comment_dataset_mentions")
@patch("transformation.pipeline.load_entity_alias_dictionary")
@patch("transformation.pipeline.prepare_incremental_comments")
@patch("transformation.pipeline.validate_comment_dataset")
@patch("transformation.pipeline.parse_comment_page")
def test_process_comment_pages_skips_empty_output_datasets(
    mock_parse_comment_page,
    mock_validate_comment_dataset,
    mock_prepare_incremental_comments,
    mock_load_entity_alias_dictionary,
    mock_enrich_comment_dataset_mentions,
    mock_write_mention_snapshot,
    mock_build_video_entity_sov_metrics,
    mock_build_daily_entity_sov_metrics,
    mock_write_video_entity_sov_snapshot,
    mock_write_daily_entity_sov_snapshot,
    mock_write_silver_comments,
    mock_write_rejected_comments,
):
    mock_parse_comment_page.return_value = []
    mock_validate_comment_dataset.return_value = ([], [])
    mock_prepare_incremental_comments.return_value = {
        "existing_records": 0,
        "merged_records": 0,
        "records_to_write": [],
        "merged_comments": [],
    }
    mock_load_entity_alias_dictionary.return_value.dictionary_version = (
        "nmixx_v2"
    )
    mock_enrich_comment_dataset_mentions.return_value = []
    mock_write_mention_snapshot.return_value = Path("mentions.jsonl")
    mock_build_video_entity_sov_metrics.return_value = []
    mock_build_daily_entity_sov_metrics.return_value = []
    mock_write_video_entity_sov_snapshot.return_value = Path(
        "video_sov.jsonl"
    )
    mock_write_daily_entity_sov_snapshot.return_value = Path(
        "daily_sov.jsonl"
    )

    result = process_comment_pages([RAW_DOCUMENTS[0]])

    mock_write_silver_comments.assert_not_called()
    mock_write_rejected_comments.assert_not_called()
    mock_prepare_incremental_comments.assert_called_once_with(
        incoming_comments=[],
        video_id="video-1",
        silver_base_dir=Path("data/silver/youtube/comments"),
    )
    mock_write_mention_snapshot.assert_called_once()
    assert result["silver_records_written"] == 0
    assert result["silver_output_path"] is None
    assert result["rejected_output_path"] is None
    assert result["mention_records"] == 0
    assert result["mention_output_path"] == Path("mentions.jsonl")
    assert result["video_sov_records"] == 0
    assert result["daily_sov_records"] == 0


@patch("transformation.pipeline.write_rejected_comments")
@patch("transformation.pipeline.write_silver_comments")
@patch("transformation.pipeline.write_daily_entity_sov_snapshot")
@patch("transformation.pipeline.write_video_entity_sov_snapshot")
@patch("transformation.pipeline.build_daily_entity_sov_metrics")
@patch("transformation.pipeline.build_video_entity_sov_metrics")
@patch("transformation.pipeline.write_mention_snapshot")
@patch("transformation.pipeline.enrich_comment_dataset_mentions")
@patch("transformation.pipeline.load_entity_alias_dictionary")
@patch("transformation.pipeline.prepare_incremental_comments")
@patch("transformation.pipeline.validate_comment_dataset")
@patch("transformation.pipeline.parse_comment_page")
def test_process_comment_pages_skips_unchanged_silver_records(
    mock_parse_comment_page,
    mock_validate_comment_dataset,
    mock_prepare_incremental_comments,
    mock_load_entity_alias_dictionary,
    mock_enrich_comment_dataset_mentions,
    mock_write_mention_snapshot,
    mock_build_video_entity_sov_metrics,
    mock_build_daily_entity_sov_metrics,
    mock_write_video_entity_sov_snapshot,
    mock_write_daily_entity_sov_snapshot,
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
        "merged_comments": [unchanged_comment],
    }
    mock_load_entity_alias_dictionary.return_value.dictionary_version = (
        "nmixx_v2"
    )
    mention_records = [{"entity_type": "member"}]
    mock_enrich_comment_dataset_mentions.return_value = mention_records
    mock_write_mention_snapshot.return_value = Path("mentions.jsonl")
    mock_build_video_entity_sov_metrics.return_value = [
        {"grain": "video"}
    ]
    mock_build_daily_entity_sov_metrics.return_value = [
        {"grain": "daily"}
    ]
    mock_write_video_entity_sov_snapshot.return_value = Path(
        "video_sov.jsonl"
    )
    mock_write_daily_entity_sov_snapshot.return_value = Path(
        "daily_sov.jsonl"
    )

    result = process_comment_pages([RAW_DOCUMENTS[0]])

    mock_write_silver_comments.assert_not_called()
    mock_write_rejected_comments.assert_not_called()
    assert result["silver_records_written"] == 0
    assert result["silver_output_path"] is None
    mock_enrich_comment_dataset_mentions.assert_called_once_with(
        [unchanged_comment],
        mock_load_entity_alias_dictionary.return_value,
    )
    assert result["mention_records"] == 1
    assert result["video_sov_records"] == 1
    assert result["daily_sov_records"] == 1


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
                                "textOriginal": (
                                    "NMIXX 海嫄 吳海嫄 NMIXX"
                                ),
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
    mention_dir = tmp_path / "mentions"
    video_sov_dir = tmp_path / "video-sov"
    daily_sov_dir = tmp_path / "daily-sov"

    first_result = process_comment_pages(
        [raw_document],
        silver_base_dir=silver_dir,
        rejected_base_dir=rejected_dir,
        mention_base_dir=mention_dir,
        video_sov_base_dir=video_sov_dir,
        daily_sov_base_dir=daily_sov_dir,
    )
    reingested_document = raw_document.copy()
    reingested_document["ingested_at"] = "2026-08-20T10:30:00+00:00"
    second_result = process_comment_pages(
        [reingested_document],
        silver_base_dir=silver_dir,
        rejected_base_dir=rejected_dir,
        mention_base_dir=mention_dir,
        video_sov_base_dir=video_sov_dir,
        daily_sov_base_dir=daily_sov_dir,
    )

    assert first_result["silver_records_written"] == 1
    assert first_result["silver_output_path"].exists()
    assert second_result["existing_silver_records"] == 1
    assert second_result["silver_records_written"] == 0
    assert second_result["silver_output_path"] is None
    assert len(list(silver_dir.rglob("*_comments.jsonl"))) == 1
    assert second_result["mention_output_path"].exists()
    assert len(list(mention_dir.rglob("current_mentions.jsonl"))) == 1
    saved_mentions = [
        json.loads(line)
        for line in second_result["mention_output_path"]
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [mention["entity_id"] for mention in saved_mentions] == [
        "nmixx",
        "nmixx_haewon",
    ]
    assert [mention["mention_count"] for mention in saved_mentions] == [
        1,
        1,
    ]
    assert saved_mentions[1]["matched_aliases"] == [
        "海嫄",
        "吳海嫄",
    ]
    assert second_result["video_sov_records"] == 7
    assert second_result["daily_sov_records"] == 7
    saved_video_metrics = [
        json.loads(line)
        for line in second_result["video_sov_output_path"]
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    haewon_metric = next(
        metric
        for metric in saved_video_metrics
        if metric["entity_id"] == "nmixx_haewon"
    )
    assert haewon_metric["mention_comment_count"] == 1
    assert haewon_metric["comment_share_of_voice"] == 1.0
    assert haewon_metric["entity_share_of_voice"] == 1.0
    assert len(list(video_sov_dir.rglob("current_metrics.jsonl"))) == 1
    assert len(list(daily_sov_dir.rglob("current_metrics.jsonl"))) == 1
