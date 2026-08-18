import logging
import time
from datetime import datetime, timezone

from ingestion.youtube_client import get_comments
from storage.raw_writer import write_raw_comment_page


VIDEO_ID = "aFrQIJ5cbRc"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
    )


def main():
    start_time = time.perf_counter()
    ingested_at = datetime.now(timezone.utc)
    logger.info("pipeline_start video_id=%s", VIDEO_ID)

    try:
        first_page = get_comments(VIDEO_ID)

        logger.info(
            "Fetched first page for video_id=%s comments_received=%s",
            VIDEO_ID,
            len(first_page["items"]),
        )

        first_page_path = write_raw_comment_page(
            raw_response=first_page,
            video_id=VIDEO_ID,
            page_number=1,
            ingested_at=ingested_at,
        )
        logger.info(
            "raw_page_written video_id=%s page_number=1 output_path=%s",
            VIDEO_ID,
            first_page_path,
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

            second_page_path = write_raw_comment_page(
                raw_response=second_page,
                video_id=VIDEO_ID,
                page_number=2,
                ingested_at=ingested_at,
            )
            logger.info(
                "raw_page_written video_id=%s page_number=2 output_path=%s",
                VIDEO_ID,
                second_page_path,
            )
    except Exception as error:
        execution_time_seconds = time.perf_counter() - start_time
        logger.exception(
            "pipeline_failed video_id=%s error_type=%s "
            "execution_time_seconds=%.3f",
            VIDEO_ID,
            type(error).__name__,
            execution_time_seconds,
        )
        raise
    else:
        execution_time_seconds = time.perf_counter() - start_time
        logger.info(
            "pipeline_end video_id=%s execution_time_seconds=%.3f",
            VIDEO_ID,
            execution_time_seconds,
        )


if __name__ == "__main__":
    configure_logging()
    main()
