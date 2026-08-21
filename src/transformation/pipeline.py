from pathlib import Path

from enrichment.entity_aliases import (
    DEFAULT_ENTITY_ALIASES_PATH,
    load_entity_alias_dictionary,
)
from enrichment.mention_enricher import enrich_comment_dataset_mentions
from enrichment.topic_enricher import enrich_comment_dataset_topics
from enrichment.topic_keywords import (
    DEFAULT_TOPIC_KEYWORDS_PATH,
    load_topic_keyword_dictionary,
)
from storage.entity_sov_writer import (
    DEFAULT_GOLD_DAILY_ENTITY_SOV_DIR,
    DEFAULT_GOLD_VIDEO_ENTITY_SOV_DIR,
    write_daily_entity_sov_snapshot,
    write_video_entity_sov_snapshot,
)
from storage.mention_writer import (
    DEFAULT_SILVER_MENTIONS_DIR,
    write_mention_snapshot,
)
from storage.rejected_writer import (
    DEFAULT_REJECTED_COMMENTS_DIR,
    write_rejected_comments,
)
from storage.silver_writer import (
    DEFAULT_SILVER_COMMENTS_DIR,
    write_silver_comments,
)
from storage.topic_writer import (
    DEFAULT_SILVER_TOPICS_DIR,
    write_topic_snapshot,
)
from storage.topic_metrics_writer import (
    DEFAULT_GOLD_DAILY_TOPIC_METRICS_DIR,
    DEFAULT_GOLD_VIDEO_TOPIC_METRICS_DIR,
    write_daily_topic_metrics_snapshot,
    write_video_topic_metrics_snapshot,
)
from transformation.comment_parser import (
    parse_comment_page,
    parse_utc_timestamp,
)
from transformation.incremental import prepare_incremental_comments
from transformation.topic_metrics import (
    build_daily_topic_metrics,
    build_video_topic_metrics,
)
from transformation.entity_sov_metrics import (
    build_daily_entity_sov_metrics,
    build_video_entity_sov_metrics,
)
from validation.comment_validator import validate_comment_dataset


def process_comment_pages(
    raw_documents: list[dict],
    silver_base_dir: Path = DEFAULT_SILVER_COMMENTS_DIR,
    rejected_base_dir: Path = DEFAULT_REJECTED_COMMENTS_DIR,
    mention_base_dir: Path = DEFAULT_SILVER_MENTIONS_DIR,
    topic_base_dir: Path = DEFAULT_SILVER_TOPICS_DIR,
    video_sov_base_dir: Path = DEFAULT_GOLD_VIDEO_ENTITY_SOV_DIR,
    daily_sov_base_dir: Path = DEFAULT_GOLD_DAILY_ENTITY_SOV_DIR,
    video_topic_metrics_base_dir: Path = (
        DEFAULT_GOLD_VIDEO_TOPIC_METRICS_DIR
    ),
    daily_topic_metrics_base_dir: Path = (
        DEFAULT_GOLD_DAILY_TOPIC_METRICS_DIR
    ),
    entity_aliases_path: Path = DEFAULT_ENTITY_ALIASES_PATH,
    topic_keywords_path: Path = DEFAULT_TOPIC_KEYWORDS_PATH,
) -> dict:
    if not raw_documents:
        raise ValueError("At least one raw document is required")

    video_ids = {document["video_id"] for document in raw_documents}
    ingested_at_values = {
        document["ingested_at"] for document in raw_documents
    }

    if len(video_ids) != 1:
        raise ValueError("Raw documents must have the same video_id")

    if len(ingested_at_values) != 1:
        raise ValueError("Raw documents must have the same ingested_at")

    video_id = next(iter(video_ids))
    ingested_at = parse_utc_timestamp(next(iter(ingested_at_values)))
    parsed_comments = [
        comment
        for raw_document in raw_documents
        for comment in parse_comment_page(raw_document)
    ]
    valid_records, rejected_records = validate_comment_dataset(
        parsed_comments
    )

    incremental_result = prepare_incremental_comments(
        incoming_comments=valid_records,
        video_id=video_id,
        silver_base_dir=silver_base_dir,
    )

    records_to_write = incremental_result["records_to_write"]
    silver_output_path = None
    if records_to_write:
        silver_output_path = write_silver_comments(
            comments=records_to_write,
            video_id=video_id,
            ingested_at=ingested_at,
            base_dir=silver_base_dir,
        )

    rejected_output_path = None
    if rejected_records:
        rejected_output_path = write_rejected_comments(
            comments=rejected_records,
            video_id=video_id,
            ingested_at=ingested_at,
            base_dir=rejected_base_dir,
        )

    entity_aliases = load_entity_alias_dictionary(entity_aliases_path)
    mention_records = enrich_comment_dataset_mentions(
        incremental_result["merged_comments"],
        entity_aliases,
    )
    mention_output_path = write_mention_snapshot(
        mentions=mention_records,
        video_id=video_id,
        dictionary_version=entity_aliases.dictionary_version,
        base_dir=mention_base_dir,
    )
    video_sov_metrics = build_video_entity_sov_metrics(
        incremental_result["merged_comments"],
        mention_records,
        entity_aliases,
    )
    daily_sov_metrics = build_daily_entity_sov_metrics(
        incremental_result["merged_comments"],
        mention_records,
        entity_aliases,
    )
    video_sov_output_path = write_video_entity_sov_snapshot(
        metrics=video_sov_metrics,
        video_id=video_id,
        dictionary_version=entity_aliases.dictionary_version,
        base_dir=video_sov_base_dir,
    )
    daily_sov_output_path = write_daily_entity_sov_snapshot(
        metrics=daily_sov_metrics,
        video_id=video_id,
        dictionary_version=entity_aliases.dictionary_version,
        base_dir=daily_sov_base_dir,
    )
    topic_dictionary = load_topic_keyword_dictionary(topic_keywords_path)
    topic_records = enrich_comment_dataset_topics(
        incremental_result["merged_comments"],
        topic_dictionary,
    )
    topic_output_path = write_topic_snapshot(
        topic_records=topic_records,
        video_id=video_id,
        dictionary_version=topic_dictionary.dictionary_version,
        base_dir=topic_base_dir,
    )
    video_topic_metrics = build_video_topic_metrics(
        incremental_result["merged_comments"],
        topic_records,
        topic_dictionary,
    )
    daily_topic_metrics = build_daily_topic_metrics(
        incremental_result["merged_comments"],
        topic_records,
        topic_dictionary,
    )
    video_topic_metrics_output_path = (
        write_video_topic_metrics_snapshot(
            metrics=video_topic_metrics,
            video_id=video_id,
            dictionary_version=topic_dictionary.dictionary_version,
            base_dir=video_topic_metrics_base_dir,
        )
    )
    daily_topic_metrics_output_path = (
        write_daily_topic_metrics_snapshot(
            metrics=daily_topic_metrics,
            video_id=video_id,
            dictionary_version=topic_dictionary.dictionary_version,
            base_dir=daily_topic_metrics_base_dir,
        )
    )

    return {
        "records_parsed": len(parsed_comments),
        "valid_records": len(valid_records),
        "rejected_records": len(rejected_records),
        "existing_silver_records": incremental_result[
            "existing_records"
        ],
        "merged_silver_records": incremental_result["merged_records"],
        "silver_records_written": len(records_to_write),
        "silver_output_path": silver_output_path,
        "rejected_output_path": rejected_output_path,
        "entity_dictionary_version": entity_aliases.dictionary_version,
        "mention_records": len(mention_records),
        "group_mention_records": sum(
            mention["entity_type"] == "group"
            for mention in mention_records
        ),
        "member_mention_records": sum(
            mention["entity_type"] == "member"
            for mention in mention_records
        ),
        "mention_output_path": mention_output_path,
        "video_sov_records": len(video_sov_metrics),
        "daily_sov_records": len(daily_sov_metrics),
        "video_sov_output_path": video_sov_output_path,
        "daily_sov_output_path": daily_sov_output_path,
        "topic_dictionary_version": topic_dictionary.dictionary_version,
        "topic_records": len(topic_records),
        "topic_output_path": topic_output_path,
        "video_topic_metrics_records": len(video_topic_metrics),
        "daily_topic_metrics_records": len(daily_topic_metrics),
        "video_topic_metrics_output_path": (
            video_topic_metrics_output_path
        ),
        "daily_topic_metrics_output_path": (
            daily_topic_metrics_output_path
        ),
    }
