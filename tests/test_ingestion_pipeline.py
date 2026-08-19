from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import call, patch

from ingestion.pipeline import ingest_comment_pages


INGESTED_AT = datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc)


@patch("ingestion.pipeline.write_raw_comment_page")
@patch("ingestion.pipeline.get_comments")
def test_ingest_comment_pages_stops_when_there_is_no_next_page(
    mock_get_comments,
    mock_write_raw_comment_page,
):
    page = {"items": [{"id": "comment-1"}]}
    mock_get_comments.return_value = page
    mock_write_raw_comment_page.return_value = Path("page_0001.json")

    pages_fetched = ingest_comment_pages(
        video_id="test-video-id",
        max_pages=5,
        ingested_at=INGESTED_AT,
    )

    assert pages_fetched == 1
    mock_get_comments.assert_called_once_with(
        "test-video-id",
        page_token=None,
    )
    mock_write_raw_comment_page.assert_called_once_with(
        raw_response=page,
        video_id="test-video-id",
        page_number=1,
        ingested_at=INGESTED_AT,
    )


@patch("ingestion.pipeline.write_raw_comment_page")
@patch("ingestion.pipeline.get_comments")
def test_ingest_comment_pages_stops_at_max_pages(
    mock_get_comments,
    mock_write_raw_comment_page,
):
    first_page = {
        "items": [{"id": "comment-1"}],
        "nextPageToken": "page-2-token",
    }
    second_page = {
        "items": [{"id": "comment-2"}],
        "nextPageToken": "page-3-token",
    }
    mock_get_comments.side_effect = [first_page, second_page]
    mock_write_raw_comment_page.side_effect = [
        Path("page_0001.json"),
        Path("page_0002.json"),
    ]

    pages_fetched = ingest_comment_pages(
        video_id="test-video-id",
        max_pages=2,
        ingested_at=INGESTED_AT,
    )

    assert pages_fetched == 2
    assert mock_get_comments.call_args_list == [
        call("test-video-id", page_token=None),
        call("test-video-id", page_token="page-2-token"),
    ]
    assert mock_write_raw_comment_page.call_args_list == [
        call(
            raw_response=first_page,
            video_id="test-video-id",
            page_number=1,
            ingested_at=INGESTED_AT,
        ),
        call(
            raw_response=second_page,
            video_id="test-video-id",
            page_number=2,
            ingested_at=INGESTED_AT,
        ),
    ]
