-- Purpose: Reconcile the latest publication counts with history tables and current views.
-- 用途：比對最新 publication、history tables 與 current views 的資料筆數。
-- Set the :video_id parameter in Databricks SQL Editor before running.

WITH latest_publication AS (
    SELECT
        run_id,
        video_id,
        row_counts_json
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_load_publications
    WHERE video_id = :video_id
    ORDER BY
        run_started_at DESC,
        published_at DESC,
        run_id DESC
    LIMIT 1
),
expected_counts AS (
    SELECT
        run_id,
        video_id,
        table_name,
        expected_row_count
    FROM latest_publication
    LATERAL VIEW stack(
        4,
        'gold_video_entity_sov',
        element_at(
            from_json(row_counts_json, 'MAP<STRING, BIGINT>'),
            'gold_video_entity_sov'
        ),
        'gold_daily_entity_sov',
        element_at(
            from_json(row_counts_json, 'MAP<STRING, BIGINT>'),
            'gold_daily_entity_sov'
        ),
        'gold_video_topic_metrics',
        element_at(
            from_json(row_counts_json, 'MAP<STRING, BIGINT>'),
            'gold_video_topic_metrics'
        ),
        'gold_daily_topic_metrics',
        element_at(
            from_json(row_counts_json, 'MAP<STRING, BIGINT>'),
            'gold_daily_topic_metrics'
        )
    ) stacked AS table_name, expected_row_count
),
history_counts AS (
    SELECT
        'gold_video_entity_sov' AS table_name,
        COUNT(*) AS history_row_count
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_video_entity_sov_history
    WHERE video_id = :video_id
      AND load_run_id = (SELECT run_id FROM latest_publication)

    UNION ALL

    SELECT
        'gold_daily_entity_sov',
        COUNT(*)
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_daily_entity_sov_history
    WHERE video_id = :video_id
      AND load_run_id = (SELECT run_id FROM latest_publication)

    UNION ALL

    SELECT
        'gold_video_topic_metrics',
        COUNT(*)
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_video_topic_metrics_history
    WHERE video_id = :video_id
      AND load_run_id = (SELECT run_id FROM latest_publication)

    UNION ALL

    SELECT
        'gold_daily_topic_metrics',
        COUNT(*)
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_daily_topic_metrics_history
    WHERE video_id = :video_id
      AND load_run_id = (SELECT run_id FROM latest_publication)
),
current_counts AS (
    SELECT
        'gold_video_entity_sov' AS table_name,
        COUNT(*) AS current_row_count
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_video_entity_sov
    WHERE video_id = :video_id

    UNION ALL

    SELECT
        'gold_daily_entity_sov',
        COUNT(*)
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_daily_entity_sov
    WHERE video_id = :video_id

    UNION ALL

    SELECT
        'gold_video_topic_metrics',
        COUNT(*)
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_video_topic_metrics
    WHERE video_id = :video_id

    UNION ALL

    SELECT
        'gold_daily_topic_metrics',
        COUNT(*)
    FROM rselayva_dev.youtube_comment_pipeline_dev.gold_daily_topic_metrics
    WHERE video_id = :video_id
)
SELECT
    expected.run_id,
    expected.video_id,
    expected.table_name,
    expected.expected_row_count,
    history.history_row_count,
    current.current_row_count,
    CASE
        WHEN expected.expected_row_count = history.history_row_count
         AND expected.expected_row_count = current.current_row_count
        THEN 'PASS'
        ELSE 'FAIL'
    END AS reconciliation_status
FROM expected_counts AS expected
INNER JOIN history_counts AS history
    ON expected.table_name = history.table_name
INNER JOIN current_counts AS current
    ON expected.table_name = current.table_name
ORDER BY expected.table_name;
