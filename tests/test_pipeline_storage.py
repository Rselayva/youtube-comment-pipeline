from pathlib import Path, PurePosixPath

from storage.pipeline_storage import (
    DEFAULT_PIPELINE_STORAGE,
    PipelineStorage,
)


def test_default_pipeline_storage_preserves_local_data_layout():
    assert DEFAULT_PIPELINE_STORAGE.raw_comments_dir == Path(
        "data/raw/youtube/comments"
    )
    assert DEFAULT_PIPELINE_STORAGE.silver_mentions_dir == Path(
        "data/silver/youtube/comment_entity_mentions"
    )
    assert DEFAULT_PIPELINE_STORAGE.run_manifests_dir == Path(
        "data/manifests/youtube/runs"
    )


def test_pipeline_storage_can_use_a_databricks_volume_root():
    root = PurePosixPath("/Volumes/catalog/schema/volume/pipeline")

    storage = PipelineStorage.under(root)

    assert storage.raw_videos_dir == root / "raw/youtube/videos"
    assert storage.gold_daily_topic_metrics_dir == (
        root / "gold/youtube/daily_topic_metrics"
    )
    assert storage.run_manifests_dir == root / "manifests/youtube/runs"
