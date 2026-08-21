import logging
from unittest.mock import Mock, patch

import pytest
import requests

from ingestion.youtube_client import (
    BASE_URL,
    INITIAL_BACKOFF_SECONDS,
    MAX_REQUEST_ATTEMPTS,
    REQUEST_TIMEOUT_SECONDS,
    REPLIES_BASE_URL,
    RETRYABLE_STATUS_CODES,
    get_comments,
    get_replies,
    get_video_metadata,
    VIDEOS_BASE_URL,
)
from ingestion.youtube_errors import (
    YouTubeCommentsDisabledError,
    YouTubeParentCommentNotFoundError,
    YouTubeQuotaExceededError,
    YouTubeRateLimitError,
    YouTubeVideoNotFoundError,
)


def make_error_response(status_code: int, reason: str):
    response = Mock(status_code=status_code)
    response.json.return_value = {
        "error": {
            "errors": [
                {
                    "reason": reason,
                }
            ]
        }
    }
    http_error = requests.HTTPError(response=response)
    response.raise_for_status.side_effect = http_error
    return response, http_error


@patch("ingestion.youtube_client.requests.get")
def test_get_comments_raises_error_when_api_key_is_missing(mock_get: Mock):
    with patch("ingestion.youtube_client.API_KEY", None):
        with pytest.raises(ValueError, match="YOUTUBE_API_KEY is not set"):
            get_comments(video_id="test-video-id")

    mock_get.assert_not_called()


@patch("ingestion.youtube_client.requests.get")
def test_get_comments_includes_page_token(mock_get: Mock):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
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


@patch("ingestion.youtube_client.requests.get")
def test_get_comments_uses_request_timeout(mock_get: Mock):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        get_comments(video_id="test-video-id")

    assert mock_get.call_args.kwargs["timeout"] == REQUEST_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    "network_error",
    [requests.Timeout, requests.ConnectionError],
)
@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_retries_after_transient_network_error(
    mock_get: Mock,
    mock_sleep: Mock,
    network_error: type[requests.RequestException],
):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.side_effect = [network_error, mock_response]

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_comments(video_id="test-video-id")

    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(INITIAL_BACKOFF_SECONDS)
    assert result == {"items": []}


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_raises_timeout_after_max_attempts(
    mock_get: Mock,
    mock_sleep: Mock,
):
    mock_get.side_effect = requests.Timeout

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        with pytest.raises(requests.Timeout):
            get_comments(video_id="test-video-id")

    assert mock_get.call_count == MAX_REQUEST_ATTEMPTS
    assert [call.args[0] for call in mock_sleep.call_args_list] == [1, 2]


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_retries_after_retryable_server_error(
    mock_get: Mock,
    mock_sleep: Mock,
):
    failed_response = Mock(status_code=503)
    failed_response.raise_for_status.side_effect = requests.HTTPError(
        response=failed_response,
    )

    successful_response = Mock()
    successful_response.json.return_value = {"items": []}
    mock_get.side_effect = [failed_response, successful_response]

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_comments(video_id="test-video-id")

    assert 503 in RETRYABLE_STATUS_CODES
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(INITIAL_BACKOFF_SECONDS)
    assert result == {"items": []}


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_does_not_retry_after_client_error(
    mock_get: Mock,
    mock_sleep: Mock,
):
    failed_response = Mock(status_code=400)
    http_error = requests.HTTPError(response=failed_response)
    failed_response.raise_for_status.side_effect = http_error
    mock_get.return_value = failed_response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        with pytest.raises(requests.HTTPError) as raised_error:
            get_comments(video_id="test-video-id")

    assert raised_error.value is http_error
    mock_get.assert_called_once()
    mock_sleep.assert_not_called()


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_logs_retry_details(
    mock_get: Mock,
    mock_sleep: Mock,
    caplog: pytest.LogCaptureFixture,
):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.side_effect = [requests.Timeout, mock_response]

    with caplog.at_level(logging.WARNING, logger="ingestion.youtube_client"):
        with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
            get_comments(video_id="test-video-id")

    assert len(caplog.records) == 1
    log_message = caplog.records[0].getMessage()
    assert "video_id=test-video-id" in log_message
    assert "Timeout" in log_message
    assert "attempt 1/3" in log_message
    assert "retrying in 1 seconds" in log_message


@pytest.mark.parametrize(
    (
        "status_code",
        "reason",
        "expected_error_type",
        "expected_message",
    ),
    [
        (
            403,
            "quotaExceeded",
            YouTubeQuotaExceededError,
            "YouTube API quota exceeded",
        ),
        (
            403,
            "commentsDisabled",
            YouTubeCommentsDisabledError,
            "Comments are disabled for the requested video",
        ),
        (
            404,
            "videoNotFound",
            YouTubeVideoNotFoundError,
            "The requested YouTube video was not found",
        ),
    ],
)
@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_raises_domain_error_without_retry(
    mock_get: Mock,
    mock_sleep: Mock,
    status_code: int,
    reason: str,
    expected_error_type: type[RuntimeError],
    expected_message: str,
):
    response, _ = make_error_response(status_code, reason)
    mock_get.return_value = response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        with pytest.raises(expected_error_type) as raised_error:
            get_comments(video_id="test-video-id")

    assert str(raised_error.value) == expected_message
    assert raised_error.value.video_id == "test-video-id"
    assert raised_error.value.status_code == status_code
    assert raised_error.value.reason == reason
    assert "test-api-key" not in str(raised_error.value)
    mock_get.assert_called_once()
    mock_sleep.assert_not_called()


@pytest.mark.parametrize(
    ("status_code", "reason"),
    [
        (429, "rateLimitExceeded"),
        (403, "rateLimitExceeded"),
    ],
)
@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_retries_rate_limit_error(
    mock_get: Mock,
    mock_sleep: Mock,
    status_code: int,
    reason: str,
):
    failed_response, _ = make_error_response(status_code, reason)
    successful_response = Mock()
    successful_response.json.return_value = {"items": []}
    mock_get.side_effect = [failed_response, successful_response]

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_comments(video_id="test-video-id")

    assert result == {"items": []}
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(INITIAL_BACKOFF_SECONDS)


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_retries_429_without_json_error_reason(
    mock_get: Mock,
    mock_sleep: Mock,
):
    failed_response = Mock(status_code=429)
    failed_response.json.side_effect = ValueError("invalid JSON")
    failed_response.raise_for_status.side_effect = requests.HTTPError(
        response=failed_response,
    )
    successful_response = Mock()
    successful_response.json.return_value = {"items": []}
    mock_get.side_effect = [failed_response, successful_response]

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_comments(video_id="test-video-id")

    assert result == {"items": []}
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(INITIAL_BACKOFF_SECONDS)


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_comments_raises_rate_limit_error_after_max_attempts(
    mock_get: Mock,
    mock_sleep: Mock,
):
    mock_get.side_effect = [
        make_error_response(429, "rateLimitExceeded")[0]
        for _ in range(MAX_REQUEST_ATTEMPTS)
    ]

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        with pytest.raises(YouTubeRateLimitError) as raised_error:
            get_comments(video_id="test-video-id")

    assert raised_error.value.status_code == 429
    assert raised_error.value.reason == "rateLimitExceeded"
    assert mock_get.call_count == MAX_REQUEST_ATTEMPTS
    assert [call.args[0] for call in mock_sleep.call_args_list] == [1, 2]


@patch("ingestion.youtube_client.requests.get")
def test_get_replies_raises_error_when_api_key_is_missing(mock_get: Mock):
    with patch("ingestion.youtube_client.API_KEY", None):
        with pytest.raises(ValueError, match="YOUTUBE_API_KEY is not set"):
            get_replies(parent_comment_id="parent-comment-1")

    mock_get.assert_not_called()


@patch("ingestion.youtube_client.requests.get")
def test_get_replies_sends_parent_filter_and_page_token(mock_get: Mock):
    mock_response = Mock()
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_replies(
            parent_comment_id="parent-comment-1",
            max_results=75,
            page_token="reply-page-2",
        )

    mock_get.assert_called_once_with(
        REPLIES_BASE_URL,
        params={
            "part": "snippet",
            "parentId": "parent-comment-1",
            "maxResults": 75,
            "textFormat": "plainText",
            "key": "test-api-key",
            "pageToken": "reply-page-2",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    assert result == {"items": []}


@patch("ingestion.youtube_client.time.sleep")
@patch("ingestion.youtube_client.requests.get")
def test_get_replies_raises_parent_not_found_without_retry(
    mock_get: Mock,
    mock_sleep: Mock,
):
    response, _ = make_error_response(404, "commentNotFound")
    mock_get.return_value = response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        with pytest.raises(
            YouTubeParentCommentNotFoundError
        ) as raised_error:
            get_replies(parent_comment_id="missing-parent")

    assert raised_error.value.resource_id == "missing-parent"
    assert raised_error.value.status_code == 404
    assert raised_error.value.reason == "commentNotFound"
    mock_get.assert_called_once()
    mock_sleep.assert_not_called()


@patch("ingestion.youtube_client.requests.get")
def test_get_video_metadata_requests_snippet_and_statistics(mock_get: Mock):
    raw_response = {
        "items": [
            {
                "id": "video-1",
                "snippet": {"title": "Test video"},
                "statistics": {"viewCount": "100"},
            }
        ]
    }
    mock_response = Mock()
    mock_response.json.return_value = raw_response
    mock_get.return_value = mock_response

    with patch("ingestion.youtube_client.API_KEY", "test-api-key"):
        result = get_video_metadata("video-1")

    mock_get.assert_called_once_with(
        VIDEOS_BASE_URL,
        params={
            "part": "snippet,statistics",
            "id": "video-1",
            "key": "test-api-key",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    assert result == raw_response


@patch("ingestion.youtube_client.requests.get")
def test_get_video_metadata_fails_before_request_without_api_key(
    mock_get: Mock,
):
    with patch("ingestion.youtube_client.API_KEY", None):
        with pytest.raises(ValueError, match="YOUTUBE_API_KEY is not set"):
            get_video_metadata("video-1")

    mock_get.assert_not_called()
