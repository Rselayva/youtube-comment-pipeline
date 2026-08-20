import argparse
import re
from dataclasses import dataclass
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
DEFAULT_MAX_PAGES = 2
MAX_ALLOWED_PAGES = 100


@dataclass(frozen=True)
class PipelineArguments:
    video_id: str
    max_pages: int


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


def parse_max_pages(value: str) -> int:
    try:
        max_pages = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "max pages must be an integer"
        ) from error

    if not 1 <= max_pages <= MAX_ALLOWED_PAGES:
        raise argparse.ArgumentTypeError(
            f"max pages must be between 1 and {MAX_ALLOWED_PAGES}"
        )

    return max_pages


def parse_cli_args(
    argv: list[str] | None = None,
) -> PipelineArguments:
    parser = argparse.ArgumentParser(
        description="Ingest and transform comments for one YouTube video.",
    )
    parser.add_argument(
        "video",
        metavar="VIDEO",
        help="YouTube video ID or URL",
    )
    parser.add_argument(
        "--max-pages",
        type=parse_max_pages,
        default=DEFAULT_MAX_PAGES,
        help=(
            "maximum comment pages to fetch "
            f"(default: {DEFAULT_MAX_PAGES}, max: {MAX_ALLOWED_PAGES})"
        ),
    )
    args = parser.parse_args(argv)

    try:
        video_id = extract_video_id(args.video)
    except ValueError as error:
        parser.error(str(error))

    return PipelineArguments(
        video_id=video_id,
        max_pages=args.max_pages,
    )
