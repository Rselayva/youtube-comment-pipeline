-- Logical SQL contracts for the current Gold JSONL snapshots.
-- Load each snapshot into the matching table with the deployment platform's
-- JSON ingestion command. Replace rows for the same logical snapshot key.

CREATE TABLE IF NOT EXISTS gold_video_entity_sov (
    video_id VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    group_id VARCHAR NOT NULL,
    canonical_name VARCHAR NOT NULL,
    dictionary_version VARCHAR NOT NULL,
    comment_count BIGINT NOT NULL,
    mention_comment_count BIGINT NOT NULL,
    comment_share_of_voice DOUBLE NOT NULL,
    entity_type_mention_comment_count BIGINT NOT NULL,
    entity_share_of_voice DOUBLE NOT NULL,
    snapshot_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS gold_daily_entity_sov (
    video_id VARCHAR NOT NULL,
    comment_date DATE NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id VARCHAR NOT NULL,
    group_id VARCHAR NOT NULL,
    canonical_name VARCHAR NOT NULL,
    dictionary_version VARCHAR NOT NULL,
    comment_count BIGINT NOT NULL,
    mention_comment_count BIGINT NOT NULL,
    comment_share_of_voice DOUBLE NOT NULL,
    entity_type_mention_comment_count BIGINT NOT NULL,
    entity_share_of_voice DOUBLE NOT NULL,
    snapshot_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS gold_video_topic_metrics (
    video_id VARCHAR NOT NULL,
    topic_id VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    dictionary_version VARCHAR NOT NULL,
    comment_count BIGINT NOT NULL,
    topic_comment_count BIGINT NOT NULL,
    comment_share_of_voice DOUBLE NOT NULL,
    topic_comment_count_total BIGINT NOT NULL,
    topic_share_of_voice DOUBLE NOT NULL,
    snapshot_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS gold_daily_topic_metrics (
    video_id VARCHAR NOT NULL,
    comment_date DATE NOT NULL,
    topic_id VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    dictionary_version VARCHAR NOT NULL,
    comment_count BIGINT NOT NULL,
    topic_comment_count BIGINT NOT NULL,
    comment_share_of_voice DOUBLE NOT NULL,
    topic_comment_count_total BIGINT NOT NULL,
    topic_share_of_voice DOUBLE NOT NULL,
    snapshot_at TIMESTAMP NOT NULL
);
