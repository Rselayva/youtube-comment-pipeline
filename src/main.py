import logging
import time
from datetime import datetime, timezone

from ingestion.pipeline import ingest_comment_pages
from storage.raw_reader import read_raw_comment_pages
from transformation.pipeline import process_comment_pages


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
        raw_output_paths = ingest_comment_pages(
            video_id=VIDEO_ID,
            max_pages=MAX_PAGES,
            ingested_at=ingested_at,
        )
        raw_documents = read_raw_comment_pages(raw_output_paths)
        transformation_result = process_comment_pages(raw_documents)
        logger.info(
            "transformation_complete video_id=%s records_parsed=%s "
            "valid_records=%s rejected_records=%s "
            "silver_output_path=%s rejected_output_path=%s",
            VIDEO_ID,
            transformation_result["records_parsed"],
            transformation_result["valid_records"],
            transformation_result["rejected_records"],
            transformation_result["silver_output_path"],
            transformation_result["rejected_output_path"],
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
