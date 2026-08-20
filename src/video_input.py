import argparse
import re
from urllib.parse import parse_qs, urlparse


VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
PATH_VIDEO_TYPES = {
    "embed",
    "live",
    "shorts",
}


def extract_video_id(value: str) -> str:
    normalized_value = value.strip()

    if VIDEO_ID_PATTERN.fullmatch(normalized_value):
        return normalized_value

    parsed_url = urlparse(normalized_value)
    hostname = (parsed_url.hostname or "").lower()
    candidate = None

    if parsed_url.scheme not in {"http", "https"}:
        raise ValueError("Video must be an 11-character ID or YouTube URL")

    if hostname == "youtu.be":
        candidate = parsed_url.path.strip("/").split("/", 1)[0]
    elif hostname in YOUTUBE_HOSTS:
        path_parts = parsed_url.path.strip("/").split("/")

        if parsed_url.path.rstrip("/") == "/watch":
            candidate = parse_qs(parsed_url.query).get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in PATH_VIDEO_TYPES:
            candidate = path_parts[1]
    else:
        raise ValueError("URL host must be youtube.com or youtu.be")

    if candidate and VIDEO_ID_PATTERN.fullmatch(candidate):
        return candidate

    raise ValueError("YouTube URL does not contain a valid video ID")


def parse_cli_video_id(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(
        description="Ingest and transform comments for one YouTube video.",
    )
    parser.add_argument(
        "video",
        metavar="VIDEO",
        help="YouTube video ID or URL",
    )
    args = parser.parse_args(argv)

    try:
        return extract_video_id(args.video)
    except ValueError as error:
        parser.error(str(error))
