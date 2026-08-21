from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import call, patch

from ingestion.reply_pipeline import ingest_reply_pages


INGESTED_AT = datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc)


@patch("ingestion.reply_pipeline.write_raw_reply_page")
@patch("ingestion.reply_pipeline.get_replies")
def test_ingest_reply_pages_stops_without_next_page(
    mock_get_replies,
    mock_write_raw_reply_page,
):
    page = {"items": [{"id": "reply-1"}]}
    mock_get_replies.return_value = page
    mock_write_raw_reply_page.return_value = Path("reply_page_0001.json")

    paths = ingest_reply_pages(
        video_id="video-1",
        parent_comment_id="parent-1",
        max_pages=5,
        page_size=25,
        ingested_at=INGESTED_AT,
    )

    assert paths == [Path("reply_page_0001.json")]
    mock_get_replies.assert_called_once_with(
        parent_comment_id="parent-1",
        max_results=25,
        page_token=None,
    )
    mock_write_raw_reply_page.assert_called_once_with(
        raw_response=page,
        video_id="video-1",
        parent_comment_id="parent-1",
        page_number=1,
        ingested_at=INGESTED_AT,
    )


@patch("ingestion.reply_pipeline.write_raw_reply_page")
@patch("ingestion.reply_pipeline.get_replies")
def test_ingest_reply_pages_passes_tokens_and_stops_at_max_pages(
    mock_get_replies,
    mock_write_raw_reply_page,
):
    first_page = {
        "items": [{"id": "reply-1"}],
        "nextPageToken": "reply-page-2",
    }
    second_page = {
        "items": [{"id": "reply-2"}],
        "nextPageToken": "reply-page-3",
    }
    mock_get_replies.side_effect = [first_page, second_page]
    mock_write_raw_reply_page.side_effect = [
        Path("reply_page_0001.json"),
        Path("reply_page_0002.json"),
    ]

    paths = ingest_reply_pages(
        video_id="video-1",
        parent_comment_id="parent-1",
        max_pages=2,
        page_size=100,
        ingested_at=INGESTED_AT,
    )

    assert paths == [
        Path("reply_page_0001.json"),
        Path("reply_page_0002.json"),
    ]
    assert mock_get_replies.call_args_list == [
        call(
            parent_comment_id="parent-1",
            max_results=100,
            page_token=None,
        ),
        call(
            parent_comment_id="parent-1",
            max_results=100,
            page_token="reply-page-2",
        ),
    ]
    assert mock_write_raw_reply_page.call_count == 2
