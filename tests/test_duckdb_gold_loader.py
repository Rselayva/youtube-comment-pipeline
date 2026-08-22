import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from warehouse.duckdb_adapter import (
    DuckDBGoldAdapter,
    load_gold_snapshots,
)
from warehouse.gold_load_contract import GoldSnapshotLoad


VIDEO_ID = "aFrQIJ5cbRc"
ENTITY_VERSION = "nmixx_v2"
TOPIC_VERSION = "comment_topics_v1"
SCHEMA_PATH = Path("sql/gold_schema.sql")


def write_jsonl(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def make_entity_metric(daily: bool = False) -> dict:
    metric = {
        "video_id": VIDEO_ID,
        "entity_type": "member",
        "entity_id": "nmixx_haewon",
        "group_id": "nmixx",
        "canonical_name": "HAEWON",
        "dictionary_version": ENTITY_VERSION,
        "comment_count": 3,
        "mention_comment_count": 2,
        "comment_share_of_voice": 2 / 3,
        "entity_type_mention_comment_count": 2,
        "entity_share_of_voice": 1.0,
        "snapshot_at": "2026-08-21T12:00:00+00:00",
    }
    if daily:
        metric["comment_date"] = "2026-08-21"
    return metric


def make_topic_metric(daily: bool = False) -> dict:
    metric = {
        "video_id": VIDEO_ID,
        "topic_id": "vocal",
        "display_name": "Vocal",
        "dictionary_version": TOPIC_VERSION,
        "comment_count": 3,
        "topic_comment_count": 2,
        "comment_share_of_voice": 2 / 3,
        "topic_comment_count_total": 2,
        "topic_share_of_voice": 1.0,
        "snapshot_at": "2026-08-21T12:00:00+00:00",
    }
    if daily:
        metric["comment_date"] = "2026-08-21"
    return metric


def make_manifest(tmp_path: Path) -> dict:
    artifacts = {
        "gold_video_entity_sov": write_jsonl(
            tmp_path / "video_entity.jsonl",
            [make_entity_metric()],
        ),
        "gold_daily_entity_sov": write_jsonl(
            tmp_path / "daily_entity.jsonl",
            [make_entity_metric(daily=True)],
        ),
        "gold_video_topic_metrics": write_jsonl(
            tmp_path / "video_topic.jsonl",
            [make_topic_metric()],
        ),
        "gold_daily_topic_metrics": write_jsonl(
            tmp_path / "daily_topic.jsonl",
            [make_topic_metric(daily=True)],
        ),
    }
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
            "entity": ENTITY_VERSION,
            "topic": TOPIC_VERSION,
        },
        "counts": {},
        "artifacts": artifacts,
    }


def test_load_gold_snapshots_creates_typed_tables(tmp_path):
    manifest = make_manifest(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"

    loaded_rows = load_gold_snapshots(
        manifest,
        database_path,
        SCHEMA_PATH,
    )

    assert loaded_rows == {
        "gold_video_entity_sov": 1,
        "gold_daily_entity_sov": 1,
        "gold_video_topic_metrics": 1,
        "gold_daily_topic_metrics": 1,
    }
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row = connection.execute(
            """
            SELECT entity_id, mention_comment_count, snapshot_at
            FROM gold_video_entity_sov
            """
        ).fetchone()
        daily_date = connection.execute(
            "SELECT comment_date FROM gold_daily_entity_sov"
        ).fetchone()[0]

    assert row[0:2] == ("nmixx_haewon", 2)
    assert row[2] == datetime(2026, 8, 21, 12, 0)
    assert daily_date.isoformat() == "2026-08-21"


def test_load_gold_snapshots_replaces_same_logical_snapshot(tmp_path):
    manifest = make_manifest(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"
    load_gold_snapshots(manifest, database_path, SCHEMA_PATH)
    replacement = make_entity_metric()
    replacement["mention_comment_count"] = 3
    write_jsonl(
        manifest["artifacts"]["gold_video_entity_sov"],
        [replacement],
    )

    load_gold_snapshots(manifest, database_path, SCHEMA_PATH)

    with duckdb.connect(str(database_path), read_only=True) as connection:
        count, mention_count = connection.execute(
            """
            SELECT COUNT(*), MAX(mention_comment_count)
            FROM gold_video_entity_sov
            """
        ).fetchone()
    assert (count, mention_count) == (1, 3)


def test_load_gold_snapshots_replaces_snapshot_with_zero_rows(tmp_path):
    manifest = make_manifest(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"
    load_gold_snapshots(manifest, database_path, SCHEMA_PATH)
    write_jsonl(
        manifest["artifacts"]["gold_daily_topic_metrics"],
        [],
    )

    loaded_rows = load_gold_snapshots(
        manifest,
        database_path,
        SCHEMA_PATH,
    )

    assert loaded_rows["gold_daily_topic_metrics"] == 0
    with duckdb.connect(str(database_path), read_only=True) as connection:
        row_count = connection.execute(
            "SELECT COUNT(*) FROM gold_daily_topic_metrics"
        ).fetchone()[0]
    assert row_count == 0


def test_load_gold_snapshots_rolls_back_all_tables_on_failure(tmp_path):
    manifest = make_manifest(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"
    load_gold_snapshots(manifest, database_path, SCHEMA_PATH)
    replacement = make_entity_metric()
    replacement["mention_comment_count"] = 3
    write_jsonl(
        manifest["artifacts"]["gold_video_entity_sov"],
        [replacement],
    )
    invalid_topic = make_topic_metric(daily=True)
    invalid_topic["unexpected_column"] = "invalid"
    write_jsonl(
        manifest["artifacts"]["gold_daily_topic_metrics"],
        [invalid_topic],
    )

    with pytest.raises(duckdb.BinderException):
        load_gold_snapshots(manifest, database_path, SCHEMA_PATH)

    with duckdb.connect(str(database_path), read_only=True) as connection:
        mention_count = connection.execute(
            """
            SELECT mention_comment_count
            FROM gold_video_entity_sov
            """
        ).fetchone()[0]
    assert mention_count == 2


def test_load_gold_snapshots_rejects_artifact_lineage_mismatch(tmp_path):
    manifest = make_manifest(tmp_path)
    mismatched = make_topic_metric()
    mismatched["video_id"] = "bbbbbbbbbbb"
    write_jsonl(
        manifest["artifacts"]["gold_video_topic_metrics"],
        [mismatched],
    )

    with pytest.raises(ValueError, match="artifact lineage mismatch"):
        load_gold_snapshots(
            manifest,
            tmp_path / "warehouse.duckdb",
            SCHEMA_PATH,
        )


def test_load_gold_snapshots_rejects_failed_manifest(tmp_path):
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
        load_gold_snapshots(
            manifest,
            tmp_path / "warehouse.duckdb",
            SCHEMA_PATH,
        )


def test_load_gold_snapshots_rejects_missing_artifact_before_connecting(
    tmp_path,
):
    manifest = make_manifest(tmp_path)
    manifest["artifacts"]["gold_daily_topic_metrics"].unlink()
    database_path = tmp_path / "warehouse.duckdb"

    with pytest.raises(FileNotFoundError, match="Gold artifact not found"):
        load_gold_snapshots(manifest, database_path, SCHEMA_PATH)

    assert not database_path.exists()


def test_load_gold_snapshots_rejects_missing_schema_before_connecting(
    tmp_path,
):
    manifest = make_manifest(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"

    with pytest.raises(FileNotFoundError, match="Gold schema not found"):
        load_gold_snapshots(
            manifest,
            database_path,
            tmp_path / "missing_schema.sql",
        )

    assert not database_path.exists()


def test_duckdb_adapter_rejects_undeclared_table_before_connecting(
    tmp_path,
):
    source_path = tmp_path / "snapshot.jsonl"
    source_path.write_text("", encoding="utf-8")
    database_path = tmp_path / "warehouse.duckdb"
    adapter = DuckDBGoldAdapter(database_path, SCHEMA_PATH)
    snapshot = GoldSnapshotLoad(
        table_name="undeclared_table",
        source_uri=str(source_path),
        video_id=VIDEO_ID,
        dictionary_version=ENTITY_VERSION,
    )

    with pytest.raises(ValueError, match="Unsupported Gold table names"):
        adapter.load_snapshots((snapshot,))

    assert not database_path.exists()
