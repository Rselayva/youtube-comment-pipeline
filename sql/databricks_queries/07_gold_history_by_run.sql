-- Purpose: Review Gold history row counts by run, dataset, and dictionary version.
-- 用途：依 run、資料集與字典版本查看 Gold history 的資料筆數。
-- Set the :video_id parameter in Databricks SQL Editor before running.

SELECT
    'gold_video_entity_sov' AS dataset_name,
    video_id,
    load_run_id,
    dictionary_version,
    COUNT(*) AS row_count,
    MAX(loaded_at) AS loaded_at
FROM `rselayva_dev`.`youtube_comment_pipeline_dev`.`gold_video_entity_sov_history`
WHERE video_id = :video_id
GROUP BY
    video_id,
    load_run_id,
    dictionary_version

UNION ALL

SELECT
    'gold_daily_entity_sov',
    video_id,
    load_run_id,
    dictionary_version,
    COUNT(*),
    MAX(loaded_at)
FROM `rselayva_dev`.`youtube_comment_pipeline_dev`.`gold_daily_entity_sov_history`
WHERE video_id = :video_id
GROUP BY
    video_id,
    load_run_id,
    dictionary_version

UNION ALL

SELECT
    'gold_video_topic_metrics',
    video_id,
    load_run_id,
    dictionary_version,
    COUNT(*),
    MAX(loaded_at)
FROM `rselayva_dev`.`youtube_comment_pipeline_dev`.`gold_video_topic_metrics_history`
WHERE video_id = :video_id
GROUP BY
    video_id,
    load_run_id,
    dictionary_version

UNION ALL

SELECT
    'gold_daily_topic_metrics',
    video_id,
    load_run_id,
    dictionary_version,
    COUNT(*),
    MAX(loaded_at)
FROM `rselayva_dev`.`youtube_comment_pipeline_dev`.`gold_daily_topic_metrics_history`
WHERE video_id = :video_id
GROUP BY
    video_id,
    load_run_id,
    dictionary_version

ORDER BY
    loaded_at DESC,
    load_run_id DESC,
    dataset_name;
