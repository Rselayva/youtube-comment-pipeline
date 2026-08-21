import json
from datetime import datetime, timezone

import pytest

from storage.run_manifest_reader import (
    list_run_manifest_files,
    read_latest_run_manifest,
    read_run_manifest,
)
from storage.run_manifest_writer import write_run_manifest


VIDEO_ID = "aFrQIJ5cbRc"


def make_manifest(started_at: datetime, status: str = "succeeded") -> dict:
    manifest = {
        "schema_version": 1,
        "run_id": f"{VIDEO_ID}_{started_at:%Y%m%dT%H%M%S%fZ}",
        "status": status,
        "video_id": VIDEO_ID,
        "started_at": started_at,
        "completed_at": started_at,
        "execution_time_seconds": 0.0,
        "parameters": {"max_pages": 2, "page_size": 10},
        "dictionary_versions": {},
        "counts": {"raw_comment_pages": 0},
        "artifacts": {
            "raw_video_metadata": None,
            "raw_comment_pages": [],
        },
    }
    if status == "failed":
        manifest["failure"] = {
            "stage": "comment_ingestion",
            "error_type": "RuntimeError",
        }
    return manifest


def test_list_and_read_latest_run_manifest_use_timestamped_paths(tmp_path):
    older = make_manifest(
        datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
    )
    newer = make_manifest(
        datetime(2026, 8, 21, 9, 0, tzinfo=timezone.utc),
        status="failed",
    )
    older_path = write_run_manifest(older, tmp_path)
    newer_path = write_run_manifest(newer, tmp_path)

    paths = list_run_manifest_files(VIDEO_ID, tmp_path)
    latest = read_latest_run_manifest(VIDEO_ID, tmp_path)

    assert paths == [older_path, newer_path]
    assert latest["run_id"] == newer["run_id"]
    assert latest["status"] == "failed"
    assert latest["failure"]["stage"] == "comment_ingestion"
    assert latest["started_at"] == newer["started_at"]


def test_read_latest_run_manifest_returns_none_without_history(tmp_path):
    assert read_latest_run_manifest(VIDEO_ID, tmp_path) is None


def test_read_run_manifest_rejects_invalid_schema(tmp_path):
    path = tmp_path / "invalid_run.json"
    path.write_text(
        json.dumps({"schema_version": 1}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema mismatch"):
        read_run_manifest(path)


def test_read_latest_run_manifest_rejects_directory_video_mismatch(
    tmp_path,
):
    manifest = make_manifest(
        datetime(2026, 8, 21, 9, 0, tzinfo=timezone.utc)
    )
    source_path = write_run_manifest(manifest, tmp_path / "source")
    different_video_id = "bbbbbbbbbbb"
    target_dir = tmp_path / different_video_id / "2026-08-21"
    target_dir.mkdir(parents=True)
    target_path = target_dir / source_path.name
    target_path.write_bytes(source_path.read_bytes())

    with pytest.raises(
        ValueError,
        match="video_id does not match its directory",
    ):
        read_latest_run_manifest(different_video_id, tmp_path)


def test_list_run_manifest_files_rejects_non_normalized_video_id(tmp_path):
    with pytest.raises(
        ValueError,
        match="video_id must be a normalized 11-character ID",
    ):
        list_run_manifest_files("../outside", tmp_path)
