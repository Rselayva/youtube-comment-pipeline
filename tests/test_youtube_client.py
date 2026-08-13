from unittest.mock import Mock, patch

import pytest
import requests

from src.ingestion.youtube_client import (
    BASE_URL,
    INITIAL_BACKOFF_SECONDS,
    MAX_REQUEST_ATTEMPTS,
    REQUEST_TIMEOUT_SECONDS,
    get_comments,
)


@patch("src.ingestion.youtube_client.requests.get")
def test_get_comments_raises_error_when_api_key_is_missing(mock_get: Mock):
    with patch("src.ingestion.youtube_client.API_KEY", None):
        with pytest.raises(ValueError, match="YOUTUBE_API_KEY is not set"):
            get_comments(video_id="test-video-id")

    mock_get.assert_not_called()


@patch("src.ingestion.youtube_client.requests.get")
def test_get_comments_includes_page_token(mock_get: Mock):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    with patch("src.ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_comments(
            video_id="test-video-id",
            max_results=25,
            page_token="test-page-token",
        )

    mock_get.assert_called_once_with(
        BASE_URL,
        params={
            "part": "snippet",
            "videoId": "test-video-id",
            "maxResults": 25,
            "textFormat": "plainText",
            "key": "test-api-key",
            "pageToken": "test-page-token",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    mock_response.raise_for_status.assert_called_once_with()
    assert result == {"items": []}


@patch("src.ingestion.youtube_client.requests.get")
def test_get_comments_uses_request_timeout(mock_get: Mock):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    with patch("src.ingestion.youtube_client.API_KEY", "test-api-key"):
        get_comments(video_id="test-video-id")

    assert mock_get.call_args.kwargs["timeout"] == REQUEST_TIMEOUT_SECONDS


@patch("src.ingestion.youtube_client.time.sleep")
@patch("src.ingestion.youtube_client.requests.get")
def test_get_comments_retries_after_timeout(mock_get: Mock, mock_sleep: Mock):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.side_effect = [requests.Timeout, mock_response]

    with patch("src.ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_comments(video_id="test-video-id")

    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(INITIAL_BACKOFF_SECONDS)
    assert result == {"items": []}


@patch("src.ingestion.youtube_client.time.sleep")
@patch("src.ingestion.youtube_client.requests.get")
def test_get_comments_raises_timeout_after_max_attempts(
    mock_get: Mock,
    mock_sleep: Mock,
):
    mock_get.side_effect = requests.Timeout

    with patch("src.ingestion.youtube_client.API_KEY", "test-api-key"):
        with pytest.raises(requests.Timeout):
            get_comments(video_id="test-video-id")

    assert mock_get.call_count == MAX_REQUEST_ATTEMPTS
    assert [call.args[0] for call in mock_sleep.call_args_list] == [1, 2]
