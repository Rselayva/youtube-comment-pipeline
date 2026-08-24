-- Purpose: Track daily vocal, dance, and visual topic trends for one video.
-- 用途：追蹤指定影片中 vocal、dance 與 visual 主題的每日聲量趨勢。
-- Set the :video_id parameter in Databricks SQL Editor before running.

SELECT
    video_id,
    comment_date,
    topic_id,
    display_name AS topic_name,
    topic_comment_count,
    comment_count,
    comment_share_of_voice,
    topic_share_of_voice,
    dictionary_version,
    snapshot_at
FROM `rselayva_dev`.`youtube_comment_pipeline_dev`.`gold_daily_topic_metrics`
WHERE video_id = :video_id
  AND dictionary_version = 'comment_topics_v1'
ORDER BY
    comment_date,
    topic_name;
