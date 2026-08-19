import logging
import time
from datetime import datetime, timezone

from ingestion.pipeline import ingest_comment_pages


VIDEO_ID = "aFrQIJ5cbRc"
MAX_PAGES = 2
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
        ingest_comment_pages(
            video_id=VIDEO_ID,
            max_pages=MAX_PAGES,
            ingested_at=ingested_at,
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
