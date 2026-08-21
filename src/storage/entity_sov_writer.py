import json
from datetime import timezone
from pathlib import Path

from validation.gold_validator import validate_entity_sov_metrics


DEFAULT_GOLD_VIDEO_ENTITY_SOV_DIR = Path(
    "data/gold/youtube/video_entity_sov"
)
DEFAULT_GOLD_DAILY_ENTITY_SOV_DIR = Path(
    "data/gold/youtube/daily_entity_sov"
)


def serialize_entity_sov_metric(metric: dict) -> dict:
    serialized_metric = metric.copy()
    serialized_metric["snapshot_at"] = serialized_metric[
        "snapshot_at"
    ].astimezone(timezone.utc).isoformat()

    if "comment_date" in serialized_metric:
        serialized_metric["comment_date"] = serialized_metric[
            "comment_date"
        ].isoformat()

    return serialized_metric


def _write_entity_sov_snapshot(
    metrics: list[dict],
    video_id: str,
    dictionary_version: str,
    base_dir: Path,
) -> Path:
    output_dir = base_dir / dictionary_version / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "current_metrics.jsonl"
    temporary_path = output_dir / ".current_metrics.jsonl.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as output_file:
            for metric in metrics:
                json.dump(
                    serialize_entity_sov_metric(metric),
                    output_file,
                    ensure_ascii=False,
                )
                output_file.write("\n")

        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path


def write_video_entity_sov_snapshot(
    metrics: list[dict],
    video_id: str,
    dictionary_version: str,
    base_dir: Path = DEFAULT_GOLD_VIDEO_ENTITY_SOV_DIR,
) -> Path:
    validate_entity_sov_metrics(
        metrics,
        daily=False,
        expected_video_id=video_id,
        expected_dictionary_version=dictionary_version,
    )
    return _write_entity_sov_snapshot(
        metrics,
        video_id,
        dictionary_version,
        base_dir,
    )


def write_daily_entity_sov_snapshot(
    metrics: list[dict],
    video_id: str,
    dictionary_version: str,
    base_dir: Path = DEFAULT_GOLD_DAILY_ENTITY_SOV_DIR,
) -> Path:
    validate_entity_sov_metrics(
        metrics,
        daily=True,
        expected_video_id=video_id,
        expected_dictionary_version=dictionary_version,
    )
    return _write_entity_sov_snapshot(
        metrics,
        video_id,
        dictionary_version,
        base_dir,
    )
