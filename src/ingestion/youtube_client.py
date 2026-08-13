import os
import time

import requests
from dotenv import load_dotenv


load_dotenv()


API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
REQUEST_TIMEOUT_SECONDS = 30
MAX_REQUEST_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 1


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

    for attempt in range(MAX_REQUEST_ATTEMPTS):
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            break
        except requests.Timeout:
            if attempt == MAX_REQUEST_ATTEMPTS - 1:
                raise

            backoff_seconds = INITIAL_BACKOFF_SECONDS * (2**attempt)
            time.sleep(backoff_seconds)

    response.raise_for_status()

    return response.json()
