import os

import requests
from dotenv import load_dotenv


load_dotenv()


API_KEY = os.getenv("YOUTUBE_API_KEY")

BASE_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


def get_comments(
    video_id: str,
    max_results: int = 10,
    page_token: str | None = None,
) -> dict:
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "textFormat": "plainText",
        "key": API_KEY,
    }

    if page_token:
        params["pageToken"] = page_token

    response = requests.get(BASE_URL, params=params)

    response.raise_for_status()

    return response.json()
