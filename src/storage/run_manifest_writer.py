import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_RUN_MANIFESTS_DIR = Path("data/manifests/youtube/runs")
RUN_MANIFEST_SCHEMA_VERSION = 1


def _serialize_manifest_value(value):
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Manifest datetime values must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            key: _serialize_manifest_value(nested_value)
            for key, nested_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_serialize_manifest_value(item) for item in value]
    return value


def validate_run_manifest(manifest: dict) -> None:
    required_fields = {
        "schema_version",
        "run_id",
        "status",
        "video_id",
        "started_at",
        "completed_at",
        "execution_time_seconds",
        "parameters",
        "dictionary_versions",
        "counts",
        "artifacts",
    }
    if set(manifest) != required_fields:
        raise ValueError("Run manifest schema mismatch")
    if manifest["schema_version"] != RUN_MANIFEST_SCHEMA_VERSION:
        raise ValueError("Unsupported run manifest schema_version")
    if manifest["status"] != "succeeded":
        raise ValueError("Run manifest status must be succeeded")

    for field_name in ("run_id", "video_id"):
        value = manifest[field_name]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    for field_name in ("started_at", "completed_at"):
        value = manifest[field_name]
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(f"{field_name} must be timezone-aware")
    if manifest["completed_at"] < manifest["started_at"]:
        raise ValueError("completed_at must not precede started_at")

    execution_time = manifest["execution_time_seconds"]
    if (
        isinstance(execution_time, bool)
        or not isinstance(execution_time, (int, float))
        or execution_time < 0
    ):
        raise ValueError("execution_time_seconds must be non-negative")

    for field_name in (
        "parameters",
        "dictionary_versions",
        "counts",
        "artifacts",
    ):
        if not isinstance(manifest[field_name], dict):
            raise ValueError(f"{field_name} must be an object")


def write_run_manifest(
    manifest: dict,
    base_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> Path:
    validate_run_manifest(manifest)
    started_at_utc = manifest["started_at"].astimezone(timezone.utc)
    run_date = started_at_utc.strftime("%Y-%m-%d")
    run_timestamp = started_at_utc.strftime("%Y%m%dT%H%M%S%fZ")
    video_id = manifest["video_id"]

    output_dir = base_dir / video_id / run_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_timestamp}_run.json"
    temporary_path = output_dir / f".{output_path.name}.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as output_file:
            json.dump(
                _serialize_manifest_value(manifest),
                output_file,
                ensure_ascii=False,
                indent=2,
            )
            output_file.write("\n")

        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path
