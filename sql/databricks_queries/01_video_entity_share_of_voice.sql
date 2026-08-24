-- Purpose: Rank NMIXX members by video-level mention share of voice.
-- 用途：依影片層級的留言提及聲量，排名 NMIXX 成員。
-- Set the :video_id parameter in Databricks SQL Editor before running.

SELECT
    video_id,
    canonical_name AS member_name,
    mention_comment_count,
    comment_count,
    comment_share_of_voice,
    entity_type_mention_comment_count,
    entity_share_of_voice,
    dictionary_version,
    snapshot_at
FROM rselayva_dev.youtube_comment_pipeline_dev.gold_video_entity_sov
WHERE video_id = :video_id
  AND dictionary_version = 'nmixx_v2'
  AND entity_type = 'member'
ORDER BY
    mention_comment_count DESC,
    member_name;
