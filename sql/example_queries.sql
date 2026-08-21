-- Replace YOUR_VIDEO_ID with the target YouTube video ID.

-- Member share-of-voice ranking for one video. Group rows are intentionally
-- excluded because member and group shares use separate denominators.
SELECT
    video_id,
    canonical_name AS member_name,
    mention_comment_count,
    comment_share_of_voice,
    entity_share_of_voice,
    snapshot_at
FROM gold_video_entity_sov
WHERE video_id = 'YOUR_VIDEO_ID'
  AND dictionary_version = 'nmixx_v2'
  AND entity_type = 'member'
ORDER BY mention_comment_count DESC, member_name;

-- Explicit NMIXX group-name reach. Member mentions are not attributed to the
-- group row, so this measures direct use of NMIXX or its configured aliases.
SELECT
    video_id,
    mention_comment_count,
    comment_share_of_voice,
    snapshot_at
FROM gold_video_entity_sov
WHERE video_id = 'YOUR_VIDEO_ID'
  AND dictionary_version = 'nmixx_v2'
  AND entity_type = 'group'
  AND entity_id = 'nmixx';

-- Daily member share-of-voice trend.
SELECT
    comment_date,
    canonical_name AS member_name,
    mention_comment_count,
    comment_share_of_voice,
    entity_share_of_voice
FROM gold_daily_entity_sov
WHERE video_id = 'YOUR_VIDEO_ID'
  AND dictionary_version = 'nmixx_v2'
  AND entity_type = 'member'
ORDER BY comment_date, member_name;

-- Topic comparison for one video.
SELECT
    display_name AS topic_name,
    topic_comment_count,
    comment_share_of_voice,
    topic_share_of_voice,
    snapshot_at
FROM gold_video_topic_metrics
WHERE video_id = 'YOUR_VIDEO_ID'
  AND dictionary_version = 'comment_topics_v1'
ORDER BY topic_comment_count DESC, topic_name;

-- Daily Topic trend. comment_share_of_voice is reach among all top-level
-- comments; topic_share_of_voice is relative share among Topic assignments.
SELECT
    comment_date,
    display_name AS topic_name,
    topic_comment_count,
    comment_share_of_voice,
    topic_share_of_voice
FROM gold_daily_topic_metrics
WHERE video_id = 'YOUR_VIDEO_ID'
  AND dictionary_version = 'comment_topics_v1'
ORDER BY comment_date, topic_name;
