import json
from typing import Any

from video_input import VIDEO_ID_PATTERN
from warehouse.databricks_adapter import DatabricksGoldConfig
from warehouse.gold_load_contract import GOLD_TABLE_ARTIFACTS


def _sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def validate_latest_gold_publication(
    video_id: str,
    spark: Any,
    catalog: str,
    schema: str,
) -> dict:
    """Reconcile the latest publication with its history and current views."""
    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("video_id must be a normalized 11-character ID")

    config = DatabricksGoldConfig(catalog=catalog, schema=schema)
    video_literal = _sql_string_literal(video_id)
    publication = spark.sql(
        f"""
        SELECT run_id, table_count, total_row_count, row_counts_json
        FROM {config.publication_table_name()}
        WHERE video_id = {video_literal}
        ORDER BY run_started_at DESC, published_at DESC, run_id DESC
        LIMIT 1
        """
    ).first()
    if publication is None:
        raise ValueError(f"No published Gold run found for video: {video_id}")

    run_id, table_count, total_row_count, row_counts_json = publication
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("Latest publication run_id is invalid")
    try:
        expected_rows = json.loads(row_counts_json)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Latest publication row counts are invalid"
        ) from error
    table_names = set(GOLD_TABLE_ARTIFACTS)
    if (
        table_count != len(table_names)
        or not isinstance(expected_rows, dict)
        or set(expected_rows) != table_names
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in expected_rows.values()
        )
        or total_row_count != sum(expected_rows.values())
    ):
        raise ValueError("Latest publication row counts are invalid")

    run_literal = _sql_string_literal(run_id)
    current_rows = {}
    history_rows = {}
    for table_name in GOLD_TABLE_ARTIFACTS:
        current_count = spark.sql(
            f"SELECT COUNT(*) FROM {config.current_view_name(table_name)} "
            f"WHERE video_id = {video_literal}"
        ).first()[0]
        history_count = spark.sql(
            f"SELECT COUNT(*) FROM {config.history_table_name(table_name)} "
            f"WHERE video_id = {video_literal} "
            f"AND load_run_id = {run_literal}"
        ).first()[0]
        expected_count = expected_rows[table_name]
        if current_count != expected_count:
            raise ValueError(
                f"Current view row count mismatch: {table_name}"
            )
        if history_count != expected_count:
            raise ValueError(
                f"History row count mismatch: {table_name}"
            )
        current_rows[table_name] = current_count
        history_rows[table_name] = history_count

    return {
        "status": "passed",
        "catalog": catalog,
        "schema": schema,
        "video_id": video_id,
        "run_id": run_id,
        "current_rows": current_rows,
        "history_rows": history_rows,
    }
