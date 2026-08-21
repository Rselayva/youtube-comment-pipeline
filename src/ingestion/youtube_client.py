import logging
import os
import time

import requests
from dotenv import load_dotenv

from ingestion.youtube_errors import (
    YouTubeAPIError,
    YouTubeCommentsDisabledError,
    YouTubeParentCommentNotFoundError,
    YouTubeQuotaExceededError,
    YouTubeRateLimitError,
    YouTubeVideoNotFoundError,
)


load_dotenv()


logger = logging.getLogger(__name__)

API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
REPLIES_BASE_URL = "https://www.googleapis.com/youtube/v3/comments"
VIDEOS_BASE_URL = "https://www.googleapis.com/youtube/v3/videos"
REQUEST_TIMEOUT_SECONDS = 30
MAX_REQUEST_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 1
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
RATE_LIMIT_REASONS = {
    "rateLimitExceeded",
    "userRateLimitExceeded",
}


def extract_error_reason(response: requests.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None

    error_payload = payload.get("error")

    if not isinstance(error_payload, dict):
        return None

    errors = error_payload.get("errors", [])

    if not errors or not isinstance(errors[0], dict):
        return None

    reason = errors[0].get("reason")
    return reason if isinstance(reason, str) else None


def classify_http_error(
    error: requests.HTTPError,
    resource_id: str | None,
) -> YouTubeAPIError | None:
    response = error.response
    status_code = response.status_code if response is not None else None
    reason = extract_error_reason(response) if response is not None else None

    if status_code == 429 or reason in RATE_LIMIT_REASONS:
        return YouTubeRateLimitError(
            "YouTube API rate limit exceeded",
            resource_id,
            status_code,
            reason,
        )

    if reason == "quotaExceeded":
        return YouTubeQuotaExceededError(
            "YouTube API quota exceeded",
            resource_id,
            status_code,
            reason,
        )

    if reason == "commentsDisabled":
        return YouTubeCommentsDisabledError(
            "Comments are disabled for the requested video",
            resource_id,
            status_code,
            reason,
        )

    if reason == "videoNotFound":
        return YouTubeVideoNotFoundError(
            "The requested YouTube video was not found",
            resource_id,
            status_code,
            reason,
        )

    if reason == "commentNotFound":
        return YouTubeParentCommentNotFoundError(
            "The requested parent comment was not found",
            resource_id,
            status_code,
            reason,
        )

    return None


def request_youtube_page(
    base_url: str,
    params: dict,
    log_context: str,
    resource_id: str | None,
) -> dict:
    for attempt in range(MAX_REQUEST_ATTEMPTS):
        try:
            response = requests.get(
                base_url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            break
        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
        ) as error:
            retry_error = error

            if isinstance(error, requests.HTTPError):
                status_code = (
                    error.response.status_code
                    if error.response is not None
                    else None
                )
                domain_error = classify_http_error(error, resource_id)

                if isinstance(domain_error, YouTubeRateLimitError):
                    retry_error = domain_error
                elif domain_error is not None:
                    raise domain_error from error
                elif status_code not in RETRYABLE_STATUS_CODES:
                    raise

            if attempt == MAX_REQUEST_ATTEMPTS - 1:
                if retry_error is error:
                    raise
                raise retry_error from error

            backoff_seconds = INITIAL_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "YouTube API request failed for %s with %s; "
                "attempt %s/%s, retrying in %s seconds",
                log_context,
                type(retry_error).__name__,
                attempt + 1,
                MAX_REQUEST_ATTEMPTS,
                backoff_seconds,
            )
            time.sleep(backoff_seconds)

    return response.json()


def get_comments(
    video_id: str,
    max_results: int = 10,
    page_token: str | None = None,
) -> dict:
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY is not set")

    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "textFormat": "plainText",
        "key": API_KEY,
    }

    if page_token:
        params["pageToken"] = page_token

    return request_youtube_page(
        base_url=BASE_URL,
        params=params,
        log_context=f"video_id={video_id}",
        resource_id=video_id,
    )


def get_replies(
    parent_comment_id: str,
    max_results: int = 100,
    page_token: str | None = None,
) -> dict:
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY is not set")

    params = {
        "part": "snippet",
        "parentId": parent_comment_id,
        "maxResults": max_results,
        "textFormat": "plainText",
        "key": API_KEY,
    }

    if page_token:
        params["pageToken"] = page_token

    return request_youtube_page(
        base_url=REPLIES_BASE_URL,
        params=params,
        log_context=f"parent_comment_id={parent_comment_id}",
        resource_id=parent_comment_id,
    )


def get_video_metadata(video_id: str) -> dict:
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY is not set")

    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": API_KEY,
    }

    return request_youtube_page(
        base_url=VIDEOS_BASE_URL,
        params=params,
        log_context=f"video_id={video_id}",
        resource_id=video_id,
    )
