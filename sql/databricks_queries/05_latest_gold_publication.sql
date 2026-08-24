-- Purpose: Inspect the latest successfully published Gold run for one video.
-- 用途：查看指定影片最近一次成功發布的 Gold run 與預期資料筆數。
-- Set the :video_id parameter in Databricks SQL Editor before running.

SELECT
    run_id,
    video_id,
    run_started_at,
    published_at,
    table_count,
    total_row_count,
    from_json(
        row_counts_json,
        'MAP<STRING, BIGINT>'
    ) AS row_counts
FROM rselayva_dev.youtube_comment_pipeline_dev.gold_load_publications
WHERE video_id = :video_id
ORDER BY
    run_started_at DESC,
    published_at DESC,
    run_id DESC
LIMIT 1;
