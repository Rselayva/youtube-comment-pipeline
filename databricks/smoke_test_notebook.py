# Databricks notebook source
# MAGIC %md
# MAGIC # YouTube Comment Pipeline — Databricks Gold Smoke Test
# MAGIC
# MAGIC Use a dedicated schema whose name contains `smoke` or `test`.
# MAGIC This notebook writes anonymous fixtures only.

# COMMAND ----------
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path


dbutils.widgets.text("catalog", "", "Unity Catalog catalog")
dbutils.widgets.text(
    "schema",
    "youtube_comment_pipeline_smoke",
    "Dedicated smoke-test schema",
)
dbutils.widgets.text("volume", "smoke_data", "Fixture Volume")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()

identifier_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
for field_name, value in {
    "catalog": catalog,
    "schema": schema,
    "volume": volume,
}.items():
    if not identifier_pattern.fullmatch(value):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, and underscores"
        )
if not any(token in schema.lower() for token in ("smoke", "test")):
    raise ValueError("Smoke test schema name must contain smoke or test")


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src").is_dir():
            return candidate
    raise RuntimeError("Could not locate repository src directory")


repo_root = find_repo_root(Path.cwd())
sys.path.insert(0, str(repo_root / "src"))

from load_gold_databricks import load_gold_to_databricks
from storage.run_manifest_writer import write_run_manifest
from warehouse.databricks_adapter import DatabricksGoldConfig

# COMMAND ----------
video_id = "smokeTst001"
started_at = datetime.now(timezone.utc)
run_timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
run_id = f"{video_id}_{run_timestamp}"
fixture_root = Path(
    f"/Volumes/{catalog}/{schema}/{volume}/youtube_comment_pipeline/{run_id}"
)
fixture_root.mkdir(parents=True, exist_ok=False)


def write_jsonl(file_name: str, records: list[dict]) -> Path:
    path = fixture_root / file_name
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    return path


snapshot_at = started_at.isoformat()
entity_metric = {
    "video_id": video_id,
    "entity_type": "member",
    "entity_id": "smoke_member",
    "group_id": "smoke_group",
    "canonical_name": "SMOKE MEMBER",
    "dictionary_version": "smoke_entities_v1",
    "comment_count": 2,
    "mention_comment_count": 1,
    "comment_share_of_voice": 0.5,
    "entity_type_mention_comment_count": 1,
    "entity_share_of_voice": 1.0,
    "snapshot_at": snapshot_at,
}
topic_metric = {
    "video_id": video_id,
    "topic_id": "smoke_topic",
    "display_name": "Smoke Topic",
    "dictionary_version": "smoke_topics_v1",
    "comment_count": 2,
    "topic_comment_count": 1,
    "comment_share_of_voice": 0.5,
    "topic_comment_count_total": 1,
    "topic_share_of_voice": 1.0,
    "snapshot_at": snapshot_at,
}

artifacts = {
    "gold_video_entity_sov": write_jsonl(
        "video_entity.jsonl",
        [entity_metric],
    ),
    "gold_daily_entity_sov": write_jsonl(
        "daily_entity.jsonl",
        [{**entity_metric, "comment_date": date.today().isoformat()}],
    ),
    "gold_video_topic_metrics": write_jsonl(
        "video_topic.jsonl",
        [topic_metric],
    ),
    "gold_daily_topic_metrics": write_jsonl(
        "daily_topic.jsonl",
        [{**topic_metric, "comment_date": date.today().isoformat()}],
    ),
}

manifest = {
    "schema_version": 1,
    "run_id": run_id,
    "status": "succeeded",
    "video_id": video_id,
    "started_at": started_at,
    "completed_at": started_at,
    "execution_time_seconds": 0.0,
    "parameters": {"max_pages": 1, "page_size": 1},
    "dictionary_versions": {
        "entity": "smoke_entities_v1",
        "topic": "smoke_topics_v1",
    },
    "counts": {},
    "artifacts": artifacts,
}
manifests_dir = fixture_root / "manifests"
manifest_path = write_run_manifest(manifest, manifests_dir)

# COMMAND ----------
first_result = load_gold_to_databricks(
    video_id=video_id,
    spark=spark,
    catalog=catalog,
    schema=schema,
    manifests_dir=manifests_dir,
)
retry_result = load_gold_to_databricks(
    video_id=video_id,
    spark=spark,
    catalog=catalog,
    schema=schema,
    manifests_dir=manifests_dir,
)

expected_rows = {
    "gold_video_entity_sov": 1,
    "gold_daily_entity_sov": 1,
    "gold_video_topic_metrics": 1,
    "gold_daily_topic_metrics": 1,
}
assert first_result["loaded_rows"] == expected_rows
assert retry_result["loaded_rows"] == expected_rows

config = DatabricksGoldConfig(catalog=catalog, schema=schema)
for table_name in expected_rows:
    current_count = spark.sql(
        f"SELECT COUNT(*) FROM {config.current_view_name(table_name)} "
        f"WHERE video_id = '{video_id}'"
    ).first()[0]
    history_count = spark.sql(
        f"SELECT COUNT(*) FROM {config.history_table_name(table_name)} "
        f"WHERE load_run_id = '{run_id}'"
    ).first()[0]
    assert current_count == 1
    assert history_count == 1

publication_count = spark.sql(
    f"SELECT COUNT(*) FROM {config.publication_table_name()} "
    f"WHERE run_id = '{run_id}' AND video_id = '{video_id}'"
).first()[0]
assert publication_count == 1

smoke_result = {
    "status": "passed",
    "catalog": catalog,
    "schema": schema,
    "volume": volume,
    "video_id": video_id,
    "run_id": run_id,
    "manifest_path": str(manifest_path),
    "loaded_rows": first_result["loaded_rows"],
    "retry_was_idempotent": True,
}
print(json.dumps(smoke_result, indent=2))
