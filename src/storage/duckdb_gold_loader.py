from pathlib import Path

import duckdb

from storage.run_manifest_writer import validate_run_manifest


DEFAULT_DUCKDB_PATH = Path("data/warehouse/youtube_analytics.duckdb")
DEFAULT_GOLD_SCHEMA_PATH = Path("sql/gold_schema.sql")

GOLD_TABLE_ARTIFACTS = {
    "gold_video_entity_sov": "gold_video_entity_sov",
    "gold_daily_entity_sov": "gold_daily_entity_sov",
    "gold_video_topic_metrics": "gold_video_topic_metrics",
    "gold_daily_topic_metrics": "gold_daily_topic_metrics",
}

TABLE_DICTIONARY_TYPES = {
    "gold_video_entity_sov": "entity",
    "gold_daily_entity_sov": "entity",
    "gold_video_topic_metrics": "topic",
    "gold_daily_topic_metrics": "topic",
}


def _resolve_gold_artifacts(manifest: dict) -> dict[str, Path]:
    artifacts = {}
    for table_name, artifact_name in GOLD_TABLE_ARTIFACTS.items():
        raw_path = manifest["artifacts"].get(artifact_name)
        if not isinstance(raw_path, (str, Path)):
            raise ValueError(
                f"Missing Gold artifact path: {artifact_name}"
            )
        path = Path(raw_path)
        if not path.is_file():
            raise FileNotFoundError(f"Gold artifact not found: {path}")
        artifacts[table_name] = path
    return artifacts


def _validate_load_manifest(manifest: dict) -> dict[str, Path]:
    validate_run_manifest(manifest)
    if manifest["status"] != "succeeded":
        raise ValueError("Only succeeded run manifests can be loaded")

    dictionary_versions = manifest["dictionary_versions"]
    if set(dictionary_versions) != {"entity", "topic"}:
        raise ValueError(
            "dictionary_versions must contain entity and topic"
        )
    for dictionary_type, version in dictionary_versions.items():
        if not isinstance(version, str) or not version.strip():
            raise ValueError(
                f"dictionary_versions.{dictionary_type} must be non-empty"
            )

    return _resolve_gold_artifacts(manifest)


def _stage_and_replace_snapshot(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    source_path: Path,
    video_id: str,
    dictionary_version: str,
) -> int:
    stage_name = f"staged_{table_name}"
    if source_path.stat().st_size == 0:
        connection.execute(
            f"CREATE OR REPLACE TEMP TABLE {stage_name} AS "
            f"SELECT * FROM {table_name} WHERE FALSE"
        )
    else:
        connection.execute(
            f"CREATE OR REPLACE TEMP TABLE {stage_name} AS "
            "SELECT * FROM read_json(?, format = 'newline_delimited')",
            [str(source_path.resolve())],
        )
    row_count, invalid_lineage_count = connection.execute(
        f"""
        SELECT
            COUNT(*),
            COUNT(*) FILTER (
                WHERE video_id IS DISTINCT FROM ?
                   OR dictionary_version IS DISTINCT FROM ?
            )
        FROM {stage_name}
        """,
        [video_id, dictionary_version],
    ).fetchone()
    if invalid_lineage_count:
        raise ValueError(
            f"Gold artifact lineage mismatch for table: {table_name}"
        )

    connection.execute(
        f"DELETE FROM {table_name} "
        "WHERE video_id = ? AND dictionary_version = ?",
        [video_id, dictionary_version],
    )
    connection.execute(
        f"INSERT INTO {table_name} BY NAME SELECT * FROM {stage_name}"
    )
    return row_count


def load_gold_snapshots(
    manifest: dict,
    database_path: Path = DEFAULT_DUCKDB_PATH,
    schema_path: Path = DEFAULT_GOLD_SCHEMA_PATH,
) -> dict[str, int]:
    artifacts = _validate_load_manifest(manifest)
    if not schema_path.is_file():
        raise FileNotFoundError(f"Gold schema not found: {schema_path}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute(schema_path.read_text(encoding="utf-8"))

        loaded_rows = {}
        for table_name, source_path in artifacts.items():
            dictionary_type = TABLE_DICTIONARY_TYPES[table_name]
            dictionary_version = manifest["dictionary_versions"][
                dictionary_type
            ]
            loaded_rows[table_name] = _stage_and_replace_snapshot(
                connection=connection,
                table_name=table_name,
                source_path=source_path,
                video_id=manifest["video_id"],
                dictionary_version=dictionary_version,
            )

        connection.execute("COMMIT")
        return loaded_rows
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
