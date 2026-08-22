from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from warehouse.gold_load_contract import (
    GOLD_TABLE_ARTIFACTS,
    load_gold_manifest,
    prepare_gold_snapshot_loads,
)


VIDEO_ID = "aFrQIJ5cbRc"


def make_manifest(tmp_path) -> dict:
    artifacts = {}
    for artifact_name in GOLD_TABLE_ARTIFACTS.values():
        path = tmp_path / f"{artifact_name}.jsonl"
        path.write_text("", encoding="utf-8")
        artifacts[artifact_name] = path

    started_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    return {
        "schema_version": 1,
        "run_id": f"{VIDEO_ID}_20260821T120000000000Z",
        "status": "succeeded",
        "video_id": VIDEO_ID,
        "started_at": started_at,
        "completed_at": started_at,
        "execution_time_seconds": 0.0,
        "parameters": {"max_pages": 2, "page_size": 10},
        "dictionary_versions": {
            "entity": "nmixx_v2",
            "topic": "comment_topics_v1",
        },
        "counts": {},
        "artifacts": artifacts,
    }


def test_prepare_gold_snapshot_loads_builds_backend_neutral_contract(
    tmp_path,
):
    snapshots = prepare_gold_snapshot_loads(make_manifest(tmp_path))

    assert tuple(snapshot.table_name for snapshot in snapshots) == tuple(
        GOLD_TABLE_ARTIFACTS
    )
    assert snapshots[0].video_id == VIDEO_ID
    assert snapshots[0].run_id == make_manifest(tmp_path)["run_id"]
    assert snapshots[0].source_uri.endswith(
        "gold_video_entity_sov.jsonl"
    )
    assert snapshots[0].dictionary_version == "nmixx_v2"
    assert snapshots[-1].dictionary_version == "comment_topics_v1"


def test_load_gold_manifest_delegates_only_prepared_snapshots(tmp_path):
    manifest = make_manifest(tmp_path)
    adapter = Mock()
    adapter.load_snapshots.return_value = {
        "gold_video_entity_sov": 0,
    }

    result = load_gold_manifest(manifest, adapter)

    snapshots = adapter.load_snapshots.call_args.args[0]
    assert len(snapshots) == 4
    assert result == {"gold_video_entity_sov": 0}


def test_prepare_gold_snapshot_loads_rejects_failed_manifest(tmp_path):
    manifest = make_manifest(tmp_path)
    manifest["status"] = "failed"
    manifest["failure"] = {
        "stage": "transformation",
        "error_type": "RuntimeError",
    }

    with pytest.raises(
        ValueError,
        match="Only succeeded run manifests can be loaded",
    ):
        prepare_gold_snapshot_loads(manifest)


def test_prepare_gold_snapshot_loads_accepts_platform_uri(tmp_path):
    manifest = make_manifest(tmp_path)
    manifest["artifacts"]["gold_daily_topic_metrics"] = (
        "/Volumes/catalog/schema/gold/daily_topic.jsonl"
    )

    snapshots = prepare_gold_snapshot_loads(manifest)

    assert snapshots[-1].source_uri.startswith("/Volumes/")


def test_prepare_gold_snapshot_loads_rejects_empty_artifact_location(
    tmp_path,
):
    manifest = make_manifest(tmp_path)
    manifest["artifacts"]["gold_daily_topic_metrics"] = ""

    with pytest.raises(
        ValueError,
        match="Missing Gold artifact location",
    ):
        prepare_gold_snapshot_loads(manifest)
