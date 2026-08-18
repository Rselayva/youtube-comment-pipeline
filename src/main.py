import logging

from ingestion.youtube_client import get_comments


VIDEO_ID = "aFrQIJ5cbRc"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
    )


def main():
    first_page = get_comments(VIDEO_ID)

    logger.info(
        "Fetched first page for video_id=%s comments_received=%s",
        VIDEO_ID,
        len(first_page["items"]),
    )

    next_page_token = first_page.get("nextPageToken")

    if next_page_token:
        second_page = get_comments(
            VIDEO_ID,
            page_token=next_page_token,
        )

        logger.info(
            "Fetched second page for video_id=%s comments_received=%s",
            VIDEO_ID,
            len(second_page["items"]),
        )


if __name__ == "__main__":
    configure_logging()
    main()
