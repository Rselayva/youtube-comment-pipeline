from pathlib import Path

import duckdb

from warehouse.gold_load_contract import (
    GOLD_TABLE_ARTIFACTS,
    GoldSnapshotLoad,
    load_gold_manifest,
)


DEFAULT_DUCKDB_PATH = Path("data/warehouse/youtube_analytics.duckdb")
DEFAULT_GOLD_SCHEMA_PATH = Path("sql/gold_schema.sql")


class DuckDBGoldAdapter:
    def __init__(
        self,
        database_path: Path = DEFAULT_DUCKDB_PATH,
        schema_path: Path = DEFAULT_GOLD_SCHEMA_PATH,
    ) -> None:
        self.database_path = database_path
        self.schema_path = schema_path

    def _stage_and_replace_snapshot(
        self,
        connection: duckdb.DuckDBPyConnection,
        snapshot: GoldSnapshotLoad,
    ) -> int:
        stage_name = f"staged_{snapshot.table_name}"
        if snapshot.source_path.stat().st_size == 0:
            connection.execute(
                f"CREATE OR REPLACE TEMP TABLE {stage_name} AS "
                f"SELECT * FROM {snapshot.table_name} WHERE FALSE"
            )
        else:
            connection.execute(
                f"CREATE OR REPLACE TEMP TABLE {stage_name} AS "
                "SELECT * FROM read_json(?, "
                "format = 'newline_delimited')",
                [str(snapshot.source_path.resolve())],
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
            [snapshot.video_id, snapshot.dictionary_version],
        ).fetchone()
        if invalid_lineage_count:
            raise ValueError(
                "Gold artifact lineage mismatch for table: "
                f"{snapshot.table_name}"
            )

        connection.execute(
            f"DELETE FROM {snapshot.table_name} "
            "WHERE video_id = ? AND dictionary_version = ?",
            [snapshot.video_id, snapshot.dictionary_version],
        )
        connection.execute(
            f"INSERT INTO {snapshot.table_name} BY NAME "
            f"SELECT * FROM {stage_name}"
        )
        return row_count

    def load_snapshots(
        self,
        snapshots: tuple[GoldSnapshotLoad, ...],
    ) -> dict[str, int]:
        unsupported_tables = {
            snapshot.table_name
            for snapshot in snapshots
            if snapshot.table_name not in GOLD_TABLE_ARTIFACTS
        }
        if unsupported_tables:
            raise ValueError(
                "Unsupported Gold table names: "
                f"{sorted(unsupported_tables)}"
            )
        if not self.schema_path.is_file():
            raise FileNotFoundError(
                f"Gold schema not found: {self.schema_path}"
            )

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = duckdb.connect(str(self.database_path))
        try:
            connection.execute("BEGIN TRANSACTION")
            connection.execute(
                self.schema_path.read_text(encoding="utf-8")
            )
            loaded_rows = {
                snapshot.table_name: self._stage_and_replace_snapshot(
                    connection,
                    snapshot,
                )
                for snapshot in snapshots
            }
            connection.execute("COMMIT")
            return loaded_rows
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()


def load_gold_snapshots(
    manifest: dict,
    database_path: Path = DEFAULT_DUCKDB_PATH,
    schema_path: Path = DEFAULT_GOLD_SCHEMA_PATH,
) -> dict[str, int]:
    adapter = DuckDBGoldAdapter(database_path, schema_path)
    return load_gold_manifest(manifest, adapter)
