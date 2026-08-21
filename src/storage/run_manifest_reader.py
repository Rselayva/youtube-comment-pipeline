import json
from pathlib import Path

from storage.run_manifest_writer import (
    DEFAULT_RUN_MANIFESTS_DIR,
    validate_run_manifest,
)
from transformation.comment_parser import parse_utc_timestamp
from video_input import VIDEO_ID_PATTERN


def _validate_video_id(video_id: str) -> None:
    if not isinstance(video_id, str) or not VIDEO_ID_PATTERN.fullmatch(
        video_id
    ):
        raise ValueError("video_id must be a normalized 11-character ID")


def list_run_manifest_files(
    video_id: str,
    base_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> list[Path]:
    _validate_video_id(video_id)
    video_dir = base_dir / video_id
    if not video_dir.exists():
        return []

    return sorted(video_dir.glob("*/*_run.json"))


def read_run_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as input_file:
        manifest = json.load(input_file)

    if not {"started_at", "completed_at"} <= set(manifest):
        raise ValueError("Run manifest schema mismatch")
    for field_name in ("started_at", "completed_at"):
        manifest[field_name] = parse_utc_timestamp(manifest[field_name])

    validate_run_manifest(manifest)
    return manifest


def read_latest_run_manifest(
    video_id: str,
    base_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> dict | None:
    _validate_video_id(video_id)
    paths = list_run_manifest_files(video_id, base_dir)
    if not paths:
        return None

    manifest = read_run_manifest(paths[-1])
    if manifest["video_id"] != video_id:
        raise ValueError("Manifest video_id does not match its directory")

    return manifest
