-- Purpose: Track daily NMIXX member mention trends for one video.
-- 用途：追蹤指定影片中 NMIXX 成員的每日提及聲量趨勢。
-- Set the :video_id parameter in Databricks SQL Editor before running.

SELECT
    video_id,
    comment_date,
    canonical_name AS member_name,
    mention_comment_count,
    comment_count,
    comment_share_of_voice,
    entity_share_of_voice,
    dictionary_version,
    snapshot_at
FROM `rselayva_dev`.`youtube_comment_pipeline_dev`.`gold_daily_entity_sov`
WHERE video_id = :video_id
  AND dictionary_version = 'nmixx_v2'
  AND entity_type = 'member'
ORDER BY
    comment_date,
    member_name;
