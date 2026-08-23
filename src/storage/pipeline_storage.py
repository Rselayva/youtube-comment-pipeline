from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineStorage:
    """Physical storage locations used by one pipeline execution."""

    raw_videos_dir: Path
    raw_comments_dir: Path
    silver_comments_dir: Path
    rejected_comments_dir: Path
    silver_mentions_dir: Path
    silver_topics_dir: Path
    gold_video_entity_sov_dir: Path
    gold_daily_entity_sov_dir: Path
    gold_video_topic_metrics_dir: Path
    gold_daily_topic_metrics_dir: Path
    run_manifests_dir: Path

    @classmethod
    def under(cls, root: Path) -> "PipelineStorage":
        """Build the standard medallion layout below an arbitrary root."""
        return cls(
            raw_videos_dir=root / "raw/youtube/videos",
            raw_comments_dir=root / "raw/youtube/comments",
            silver_comments_dir=root / "silver/youtube/comments",
            rejected_comments_dir=root / "rejected/youtube/comments",
            silver_mentions_dir=(
                root / "silver/youtube/comment_entity_mentions"
            ),
            silver_topics_dir=root / "silver/youtube/comment_topics",
            gold_video_entity_sov_dir=(
                root / "gold/youtube/video_entity_sov"
            ),
            gold_daily_entity_sov_dir=(
                root / "gold/youtube/daily_entity_sov"
            ),
            gold_video_topic_metrics_dir=(
                root / "gold/youtube/video_topic_metrics"
            ),
            gold_daily_topic_metrics_dir=(
                root / "gold/youtube/daily_topic_metrics"
            ),
            run_manifests_dir=root / "manifests/youtube/runs",
        )


DEFAULT_PIPELINE_STORAGE = PipelineStorage.under(Path("data"))
