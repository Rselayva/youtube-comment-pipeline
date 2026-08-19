import logging
from datetime import datetime

from ingestion.youtube_client import get_comments
from storage.raw_writer import write_raw_comment_page


logger = logging.getLogger(__name__)


def ingest_comment_pages(
    video_id: str,
    max_pages: int,
    ingested_at: datetime,
) -> int:
    page_token = None

    for page_number in range(1, max_pages + 1):
        page = get_comments(
            video_id,
            page_token=page_token,
        )

        logger.info(
            "Fetched comment page for video_id=%s page_number=%s "
            "comments_received=%s",
            video_id,
            page_number,
            len(page["items"]),
        )

        output_path = write_raw_comment_page(
            raw_response=page,
            video_id=video_id,
            page_number=page_number,
            ingested_at=ingested_at,
        )
        logger.info(
            "raw_page_written video_id=%s page_number=%s output_path=%s",
            video_id,
            page_number,
            output_path,
        )

        page_token = page.get("nextPageToken")
        if not page_token:
            logger.info(
                "pagination_complete video_id=%s pages_fetched=%s "
                "reason=no_next_page",
                video_id,
                page_number,
            )
            return page_number

    logger.info(
        "pagination_complete video_id=%s pages_fetched=%s "
        "reason=max_pages_reached",
        video_id,
        max_pages,
    )
    return max_pages
