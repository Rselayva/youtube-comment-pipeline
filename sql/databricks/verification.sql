-- Databricks Unity Catalog deployment verification template.
--
-- Replace every placeholder before execution:
--   <CATALOG>          Deployed Unity Catalog catalog.
--   <PIPELINE_SCHEMA>  Deployed pipeline schema.
--   <PIPELINE_VOLUME>  Deployed managed Volume.
--   <VIDEO_ID>         Normalized 11-character YouTube video ID.

-- 1. Schema and Volume metadata.
DESCRIBE SCHEMA EXTENDED <CATALOG>.<PIPELINE_SCHEMA>;

SHOW VOLUMES IN <CATALOG>.<PIPELINE_SCHEMA>
LIKE '<PIPELINE_VOLUME>';

-- 2. Expected physical tables and logical current views.
WITH expected_objects (object_name, expected_type) AS (
    VALUES
        ('gold_load_publications', 'MANAGED'),
        ('gold_video_entity_sov_history', 'MANAGED'),
        ('gold_daily_entity_sov_history', 'MANAGED'),
        ('gold_video_topic_metrics_history', 'MANAGED'),
        ('gold_daily_topic_metrics_history', 'MANAGED'),
        ('gold_video_entity_sov', 'VIEW'),
        ('gold_daily_entity_sov', 'VIEW'),
        ('gold_video_topic_metrics', 'VIEW'),
        ('gold_daily_topic_metrics', 'VIEW')
),
actual_objects AS (
    SELECT
        table_name AS object_name,
        table_type AS actual_type
    FROM <CATALOG>.information_schema.tables
    WHERE table_schema = '<PIPELINE_SCHEMA>'
)
SELECT
    expected.object_name,
    expected.expected_type,
    actual.actual_type,
    CASE
        WHEN actual.actual_type = expected.expected_type THEN 'PASS'
        WHEN actual.object_name IS NULL THEN 'MISSING'
        ELSE 'TYPE_MISMATCH'
    END AS verification_status
FROM expected_objects AS expected
LEFT JOIN actual_objects AS actual
    ON expected.object_name = actual.object_name
ORDER BY expected.object_name;

-- 3. Latest published run for the selected video.
SELECT
    run_id,
    video_id,
    run_started_at,
    published_at,
    table_count,
    total_row_count,
    row_counts_json
FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_load_publications
WHERE video_id = '<VIDEO_ID>'
ORDER BY run_started_at DESC, published_at DESC, run_id DESC
LIMIT 1;

-- 4. Reconcile publication audit counts with current views and the exact
-- published history run. Every verification_status should be PASS.
WITH latest_publication AS (
    SELECT
        run_id,
        video_id,
        from_json(
            row_counts_json,
            'MAP<STRING, BIGINT>'
        ) AS expected_rows
    FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_load_publications
    WHERE video_id = '<VIDEO_ID>'
    ORDER BY run_started_at DESC, published_at DESC, run_id DESC
    LIMIT 1
),
reconciled_counts AS (
    SELECT
        'gold_video_entity_sov' AS table_name,
        element_at(
            publication.expected_rows,
            'gold_video_entity_sov'
        ) AS expected_row_count,
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_video_entity_sov
            WHERE video_id = '<VIDEO_ID>'
        ) AS current_row_count,
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_video_entity_sov_history
            WHERE video_id = '<VIDEO_ID>'
              AND load_run_id = publication.run_id
        ) AS history_row_count
    FROM latest_publication AS publication

    UNION ALL

    SELECT
        'gold_daily_entity_sov',
        element_at(
            publication.expected_rows,
            'gold_daily_entity_sov'
        ),
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_daily_entity_sov
            WHERE video_id = '<VIDEO_ID>'
        ),
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_daily_entity_sov_history
            WHERE video_id = '<VIDEO_ID>'
              AND load_run_id = publication.run_id
        )
    FROM latest_publication AS publication

    UNION ALL

    SELECT
        'gold_video_topic_metrics',
        element_at(
            publication.expected_rows,
            'gold_video_topic_metrics'
        ),
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_video_topic_metrics
            WHERE video_id = '<VIDEO_ID>'
        ),
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_video_topic_metrics_history
            WHERE video_id = '<VIDEO_ID>'
              AND load_run_id = publication.run_id
        )
    FROM latest_publication AS publication

    UNION ALL

    SELECT
        'gold_daily_topic_metrics',
        element_at(
            publication.expected_rows,
            'gold_daily_topic_metrics'
        ),
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_daily_topic_metrics
            WHERE video_id = '<VIDEO_ID>'
        ),
        (
            SELECT COUNT(*)
            FROM <CATALOG>.<PIPELINE_SCHEMA>.gold_daily_topic_metrics_history
            WHERE video_id = '<VIDEO_ID>'
              AND load_run_id = publication.run_id
        )
    FROM latest_publication AS publication
)
SELECT
    table_name,
    expected_row_count,
    current_row_count,
    history_row_count,
    CASE
        WHEN expected_row_count = current_row_count
         AND expected_row_count = history_row_count
        THEN 'PASS'
        ELSE 'FAIL'
    END AS verification_status
FROM reconciled_counts
ORDER BY table_name;
