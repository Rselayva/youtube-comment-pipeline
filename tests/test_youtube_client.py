from unittest.mock import Mock, patch

from src.ingestion.youtube_client import BASE_URL, get_comments


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
    )
    mock_response.raise_for_status.assert_called_once_with()
    assert result == {"items": []}
