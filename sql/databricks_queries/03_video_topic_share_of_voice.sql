-- Purpose: Compare video-level vocal, dance, and visual topic share of voice.
-- 用途：比較指定影片中 vocal、dance 與 visual 主題的聲量占比。
-- Set the :video_id parameter in Databricks SQL Editor before running.

SELECT
    video_id,
    topic_id,
    display_name AS topic_name,
    topic_comment_count,
    comment_count,
    comment_share_of_voice,
    topic_comment_count_total,
    topic_share_of_voice,
    dictionary_version,
    snapshot_at
FROM rselayva_dev.youtube_comment_pipeline_dev.gold_video_topic_metrics
WHERE video_id = :video_id
  AND dictionary_version = 'comment_topics_v1'
ORDER BY
    topic_comment_count DESC,
    topic_name;
