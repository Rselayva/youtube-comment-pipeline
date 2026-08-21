import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from storage.run_manifest_writer import write_run_manifest


def make_manifest() -> dict:
    return {
        "schema_version": 1,
        "run_id": "video-1_20260821T090000000000Z",
        "status": "succeeded",
        "video_id": "video-1",
        "started_at": datetime(
            2026,
            8,
            21,
            17,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        "completed_at": datetime(
            2026,
            8,
            21,
            9,
            0,
            2,
            tzinfo=timezone.utc,
        ),
        "execution_time_seconds": 2.0,
        "parameters": {"max_pages": 2, "page_size": 10},
        "dictionary_versions": {
            "entity": "nmixx_v2",
            "topic": "comment_topics_v1",
        },
        "counts": {"records_parsed": 2},
        "artifacts": {
            "raw_video_metadata": Path("data/raw/video.json"),
            "raw_comment_pages": (
                Path("data/raw/page_1.json"),
                Path("data/raw/page_2.json"),
            ),
            "silver_comments": None,
        },
    }


def test_write_run_manifest_writes_atomic_json_with_serialized_values(
    tmp_path,
):
    manifest = make_manifest()

    output_path = write_run_manifest(manifest, tmp_path)

    assert output_path == (
        tmp_path
        / "video-1"
        / "2026-08-21"
        / "20260821T090000000000Z_run.json"
    )
    saved_manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_manifest["started_at"] == "2026-08-21T09:00:00+00:00"
    assert saved_manifest["completed_at"] == (
        "2026-08-21T09:00:02+00:00"
    )
    assert saved_manifest["artifacts"]["raw_comment_pages"] == [
        str(Path("data/raw/page_1.json")),
        str(Path("data/raw/page_2.json")),
    ]
    assert saved_manifest["artifacts"]["silver_comments"] is None
    assert list(output_path.parent.iterdir()) == [output_path]


def test_write_run_manifest_does_not_mutate_input(tmp_path):
    manifest = make_manifest()
    started_at = manifest["started_at"]

    write_run_manifest(manifest, tmp_path)

    assert manifest["started_at"] is started_at
    assert isinstance(manifest["artifacts"]["raw_video_metadata"], Path)


def test_write_run_manifest_rejects_schema_mismatch_before_writing(
    tmp_path,
):
    manifest = make_manifest()
    manifest["unexpected"] = True

    with pytest.raises(ValueError, match="schema mismatch"):
        write_run_manifest(manifest, tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_write_run_manifest_rejects_naive_timestamps(tmp_path):
    manifest = make_manifest()
    manifest["completed_at"] = datetime(2026, 8, 21, 9, 0, 2)

    with pytest.raises(ValueError, match="completed_at must be timezone-aware"):
        write_run_manifest(manifest, tmp_path)
