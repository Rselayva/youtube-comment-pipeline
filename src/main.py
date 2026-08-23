import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from ingestion.pipeline import ingest_comment_pages
from ingestion.video_pipeline import ingest_video_metadata
from storage.raw_reader import read_raw_comment_pages
from storage.pipeline_storage import (
    DEFAULT_PIPELINE_STORAGE,
    PipelineStorage,
)
from storage.run_manifest_writer import (
    RUN_MANIFEST_SCHEMA_VERSION,
    write_run_manifest,
)
from transformation.pipeline import process_comment_pages
from video_input import parse_cli_args


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
    )


def build_success_run_manifest(
    video_id: str,
    max_pages: int,
    page_size: int,
    started_at: datetime,
    completed_at: datetime,
    execution_time_seconds: float,
    video_metadata_path,
    raw_output_paths,
    transformation_result: dict,
) -> dict:
    started_at_utc = started_at.astimezone(timezone.utc)
    run_timestamp = started_at_utc.strftime("%Y%m%dT%H%M%S%fZ")

    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": f"{video_id}_{run_timestamp}",
        "status": "succeeded",
        "video_id": video_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "execution_time_seconds": execution_time_seconds,
        "parameters": {
            "max_pages": max_pages,
            "page_size": page_size,
        },
        "dictionary_versions": {
            "entity": transformation_result[
                "entity_dictionary_version"
            ],
            "topic": transformation_result[
                "topic_dictionary_version"
            ],
        },
        "counts": {
            "raw_comment_pages": len(raw_output_paths),
            "records_parsed": transformation_result["records_parsed"],
            "valid_records": transformation_result["valid_records"],
            "rejected_records": transformation_result[
                "rejected_records"
            ],
            "existing_silver_records": transformation_result[
                "existing_silver_records"
            ],
            "merged_silver_records": transformation_result[
                "merged_silver_records"
            ],
            "silver_records_written": transformation_result[
                "silver_records_written"
            ],
            "entity_mention_records": transformation_result[
                "mention_records"
            ],
            "group_mention_records": transformation_result[
                "group_mention_records"
            ],
            "member_mention_records": transformation_result[
                "member_mention_records"
            ],
            "video_entity_sov_records": transformation_result[
                "video_sov_records"
            ],
            "daily_entity_sov_records": transformation_result[
                "daily_sov_records"
            ],
            "topic_records": transformation_result["topic_records"],
            "video_topic_metrics_records": transformation_result[
                "video_topic_metrics_records"
            ],
            "daily_topic_metrics_records": transformation_result[
                "daily_topic_metrics_records"
            ],
        },
        "artifacts": {
            "raw_video_metadata": video_metadata_path,
            "raw_comment_pages": raw_output_paths,
            "silver_comments": transformation_result[
                "silver_output_path"
            ],
            "rejected_comments": transformation_result[
                "rejected_output_path"
            ],
            "silver_entity_mentions": transformation_result[
                "mention_output_path"
            ],
            "silver_comment_topics": transformation_result[
                "topic_output_path"
            ],
            "gold_video_entity_sov": transformation_result[
                "video_sov_output_path"
            ],
            "gold_daily_entity_sov": transformation_result[
                "daily_sov_output_path"
            ],
            "gold_video_topic_metrics": transformation_result[
                "video_topic_metrics_output_path"
            ],
            "gold_daily_topic_metrics": transformation_result[
                "daily_topic_metrics_output_path"
            ],
        },
    }


def build_failed_run_manifest(
    video_id: str,
    max_pages: int,
    page_size: int,
    started_at: datetime,
    completed_at: datetime,
    execution_time_seconds: float,
    failure_stage: str,
    error_type: str,
    video_metadata_path=None,
    raw_output_paths=None,
    transformation_result: dict | None = None,
) -> dict:
    raw_output_paths = raw_output_paths or []
    started_at_utc = started_at.astimezone(timezone.utc)
    run_timestamp = started_at_utc.strftime("%Y%m%dT%H%M%S%fZ")
    dictionary_versions = {}
    counts = {"raw_comment_pages": len(raw_output_paths)}
    artifacts = {
        "raw_video_metadata": video_metadata_path,
        "raw_comment_pages": raw_output_paths,
    }

    if transformation_result is not None:
        dictionary_versions = {
            "entity": transformation_result[
                "entity_dictionary_version"
            ],
            "topic": transformation_result[
                "topic_dictionary_version"
            ],
        }
        counts.update(
            {
                "records_parsed": transformation_result[
                    "records_parsed"
                ],
                "valid_records": transformation_result["valid_records"],
                "rejected_records": transformation_result[
                    "rejected_records"
                ],
                "merged_silver_records": transformation_result[
                    "merged_silver_records"
                ],
                "entity_mention_records": transformation_result[
                    "mention_records"
                ],
                "topic_records": transformation_result["topic_records"],
            }
        )
        artifacts.update(
            {
                "silver_comments": transformation_result[
                    "silver_output_path"
                ],
                "rejected_comments": transformation_result[
                    "rejected_output_path"
                ],
                "silver_entity_mentions": transformation_result[
                    "mention_output_path"
                ],
                "silver_comment_topics": transformation_result[
                    "topic_output_path"
                ],
                "gold_video_entity_sov": transformation_result[
                    "video_sov_output_path"
                ],
                "gold_daily_entity_sov": transformation_result[
                    "daily_sov_output_path"
                ],
                "gold_video_topic_metrics": transformation_result[
                    "video_topic_metrics_output_path"
                ],
                "gold_daily_topic_metrics": transformation_result[
                    "daily_topic_metrics_output_path"
                ],
            }
        )

    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": f"{video_id}_{run_timestamp}",
        "status": "failed",
        "video_id": video_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "execution_time_seconds": execution_time_seconds,
        "parameters": {
            "max_pages": max_pages,
            "page_size": page_size,
        },
        "dictionary_versions": dictionary_versions,
        "counts": counts,
        "artifacts": artifacts,
        "failure": {
            "stage": failure_stage,
            "error_type": error_type,
        },
    }


def main(
    video_id: str,
    max_pages: int,
    page_size: int,
    storage: PipelineStorage = DEFAULT_PIPELINE_STORAGE,
) -> Path:
    start_time = time.perf_counter()
    ingested_at = datetime.now(timezone.utc)
    failure_stage = "video_metadata_ingestion"
    video_metadata_path = None
    raw_output_paths = []
    transformation_result = None
    logger.info("pipeline_start video_id=%s", video_id)

    try:
        video_metadata_path = ingest_video_metadata(
            video_id=video_id,
            ingested_at=ingested_at,
            raw_videos_dir=storage.raw_videos_dir,
        )
        logger.info(
            "video_metadata_complete video_id=%s output_path=%s",
            video_id,
            video_metadata_path,
        )
        failure_stage = "comment_ingestion"
        raw_output_paths = ingest_comment_pages(
            video_id=video_id,
            max_pages=max_pages,
            page_size=page_size,
            ingested_at=ingested_at,
            raw_comments_dir=storage.raw_comments_dir,
        )
        failure_stage = "raw_comment_read"
        raw_documents = read_raw_comment_pages(raw_output_paths)
        failure_stage = "transformation"
        transformation_result = process_comment_pages(
            raw_documents,
            silver_base_dir=storage.silver_comments_dir,
            rejected_base_dir=storage.rejected_comments_dir,
            mention_base_dir=storage.silver_mentions_dir,
            topic_base_dir=storage.silver_topics_dir,
            video_sov_base_dir=storage.gold_video_entity_sov_dir,
            daily_sov_base_dir=storage.gold_daily_entity_sov_dir,
            video_topic_metrics_base_dir=(
                storage.gold_video_topic_metrics_dir
            ),
            daily_topic_metrics_base_dir=(
                storage.gold_daily_topic_metrics_dir
            ),
        )
        logger.info(
            "transformation_complete video_id=%s records_parsed=%s "
            "valid_records=%s rejected_records=%s "
            "existing_silver_records=%s merged_silver_records=%s "
            "silver_records_written=%s "
            "entity_dictionary_version=%s mention_records=%s "
            "group_mention_records=%s member_mention_records=%s "
            "video_sov_records=%s daily_sov_records=%s "
            "silver_output_path=%s rejected_output_path=%s "
            "mention_output_path=%s video_sov_output_path=%s "
            "daily_sov_output_path=%s "
            "topic_dictionary_version=%s topic_records=%s "
            "video_topic_metrics_records=%s "
            "daily_topic_metrics_records=%s topic_output_path=%s "
            "video_topic_metrics_output_path=%s "
            "daily_topic_metrics_output_path=%s",
            video_id,
            transformation_result["records_parsed"],
            transformation_result["valid_records"],
            transformation_result["rejected_records"],
            transformation_result["existing_silver_records"],
            transformation_result["merged_silver_records"],
            transformation_result["silver_records_written"],
            transformation_result["entity_dictionary_version"],
            transformation_result["mention_records"],
            transformation_result["group_mention_records"],
            transformation_result["member_mention_records"],
            transformation_result["video_sov_records"],
            transformation_result["daily_sov_records"],
            transformation_result["silver_output_path"],
            transformation_result["rejected_output_path"],
            transformation_result["mention_output_path"],
            transformation_result["video_sov_output_path"],
            transformation_result["daily_sov_output_path"],
            transformation_result["topic_dictionary_version"],
            transformation_result["topic_records"],
            transformation_result["video_topic_metrics_records"],
            transformation_result["daily_topic_metrics_records"],
            transformation_result["topic_output_path"],
            transformation_result["video_topic_metrics_output_path"],
            transformation_result["daily_topic_metrics_output_path"],
        )
        completed_at = datetime.now(timezone.utc)
        execution_time_seconds = time.perf_counter() - start_time
        run_manifest = build_success_run_manifest(
            video_id=video_id,
            max_pages=max_pages,
            page_size=page_size,
            started_at=ingested_at,
            completed_at=completed_at,
            execution_time_seconds=execution_time_seconds,
            video_metadata_path=video_metadata_path,
            raw_output_paths=raw_output_paths,
            transformation_result=transformation_result,
        )
        failure_stage = "run_manifest_write"
        run_manifest_path = write_run_manifest(
            run_manifest,
            base_dir=storage.run_manifests_dir,
        )
        logger.info(
            "run_manifest_complete video_id=%s output_path=%s",
            video_id,
            run_manifest_path,
        )
    except Exception as error:
        completed_at = datetime.now(timezone.utc)
        execution_time_seconds = time.perf_counter() - start_time
        logger.exception(
            "pipeline_failed video_id=%s error_type=%s "
            "execution_time_seconds=%.3f",
            video_id,
            type(error).__name__,
            execution_time_seconds,
        )
        failed_run_manifest = build_failed_run_manifest(
            video_id=video_id,
            max_pages=max_pages,
            page_size=page_size,
            started_at=ingested_at,
            completed_at=completed_at,
            execution_time_seconds=execution_time_seconds,
            failure_stage=failure_stage,
            error_type=type(error).__name__,
            video_metadata_path=video_metadata_path,
            raw_output_paths=raw_output_paths,
            transformation_result=transformation_result,
        )
        try:
            failed_manifest_path = write_run_manifest(
                failed_run_manifest,
                base_dir=storage.run_manifests_dir,
            )
        except Exception as manifest_error:
            logger.error(
                "failure_manifest_write_failed video_id=%s "
                "original_error_type=%s manifest_error_type=%s",
                video_id,
                type(error).__name__,
                type(manifest_error).__name__,
                exc_info=True,
            )
        else:
            logger.info(
                "failure_manifest_complete video_id=%s output_path=%s",
                video_id,
                failed_manifest_path,
            )
        raise
    else:
        execution_time_seconds = time.perf_counter() - start_time
        logger.info(
            "pipeline_end video_id=%s execution_time_seconds=%.3f",
            video_id,
            execution_time_seconds,
        )
        return run_manifest_path


def run_cli():
    configure_logging()
    args = parse_cli_args()
    main(
        video_id=args.video_id,
        max_pages=args.max_pages,
        page_size=args.page_size,
    )


if __name__ == "__main__":
    run_cli()
