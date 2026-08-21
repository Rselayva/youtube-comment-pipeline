import logging
from datetime import datetime
from pathlib import Path

from ingestion.youtube_client import get_replies
from storage.raw_reply_writer import write_raw_reply_page


logger = logging.getLogger(__name__)


def ingest_reply_pages(
    video_id: str,
    parent_comment_id: str,
    max_pages: int,
    page_size: int,
    ingested_at: datetime,
) -> list[Path]:
    page_token = None
    raw_output_paths = []

    for page_number in range(1, max_pages + 1):
        page = get_replies(
            parent_comment_id=parent_comment_id,
            max_results=page_size,
            page_token=page_token,
        )
        logger.info(
            "Fetched reply page for video_id=%s parent_comment_id=%s "
            "page_number=%s replies_received=%s",
            video_id,
            parent_comment_id,
            page_number,
            len(page["items"]),
        )

        output_path = write_raw_reply_page(
            raw_response=page,
            video_id=video_id,
            parent_comment_id=parent_comment_id,
            page_number=page_number,
            ingested_at=ingested_at,
        )
        raw_output_paths.append(output_path)
        logger.info(
            "raw_reply_page_written video_id=%s parent_comment_id=%s "
            "page_number=%s output_path=%s",
            video_id,
            parent_comment_id,
            page_number,
            output_path,
        )

        page_token = page.get("nextPageToken")
        if not page_token:
            logger.info(
                "reply_pagination_complete video_id=%s "
                "parent_comment_id=%s pages_fetched=%s "
                "reason=no_next_page",
                video_id,
                parent_comment_id,
                page_number,
            )
            return raw_output_paths

    logger.info(
        "reply_pagination_complete video_id=%s parent_comment_id=%s "
        "pages_fetched=%s reason=max_pages_reached",
        video_id,
        parent_comment_id,
        max_pages,
    )
    return raw_output_paths
