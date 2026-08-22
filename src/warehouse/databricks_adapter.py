import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from warehouse.gold_load_contract import (
    GOLD_TABLE_ARTIFACTS,
    GoldSnapshotLoad,
)


UNITY_CATALOG_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PUBLICATION_TABLE_NAME = "gold_load_publications"

SPARK_JSON_SCHEMAS = {
    "gold_video_entity_sov": """
        video_id STRING,
        entity_type STRING,
        entity_id STRING,
        group_id STRING,
        canonical_name STRING,
        dictionary_version STRING,
        comment_count BIGINT,
        mention_comment_count BIGINT,
        comment_share_of_voice DOUBLE,
        entity_type_mention_comment_count BIGINT,
        entity_share_of_voice DOUBLE,
        snapshot_at TIMESTAMP
    """,
    "gold_daily_entity_sov": """
        video_id STRING,
        comment_date DATE,
        entity_type STRING,
        entity_id STRING,
        group_id STRING,
        canonical_name STRING,
        dictionary_version STRING,
        comment_count BIGINT,
        mention_comment_count BIGINT,
        comment_share_of_voice DOUBLE,
        entity_type_mention_comment_count BIGINT,
        entity_share_of_voice DOUBLE,
        snapshot_at TIMESTAMP
    """,
    "gold_video_topic_metrics": """
        video_id STRING,
        topic_id STRING,
        display_name STRING,
        dictionary_version STRING,
        comment_count BIGINT,
        topic_comment_count BIGINT,
        comment_share_of_voice DOUBLE,
        topic_comment_count_total BIGINT,
        topic_share_of_voice DOUBLE,
        snapshot_at TIMESTAMP
    """,
    "gold_daily_topic_metrics": """
        video_id STRING,
        comment_date DATE,
        topic_id STRING,
        display_name STRING,
        dictionary_version STRING,
        comment_count BIGINT,
        topic_comment_count BIGINT,
        comment_share_of_voice DOUBLE,
        topic_comment_count_total BIGINT,
        topic_share_of_voice DOUBLE,
        snapshot_at TIMESTAMP
    """,
}


def _validate_identifier(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not UNITY_CATALOG_IDENTIFIER_PATTERN.fullmatch(value)
    ):
        raise ValueError(
            f"{field_name} must be a valid Unity Catalog identifier"
        )


def _sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _schema_column_names(schema: str) -> tuple[str, ...]:
    return tuple(
        line.strip().rstrip(",").split()[0]
        for line in schema.splitlines()
        if line.strip()
    )


@dataclass(frozen=True)
class DatabricksGoldConfig:
    catalog: str
    schema: str

    def __post_init__(self) -> None:
        _validate_identifier(self.catalog, "catalog")
        _validate_identifier(self.schema, "schema")

    def qualified_name(self, object_name: str) -> str:
        _validate_identifier(object_name, "object_name")
        return f"`{self.catalog}`.`{self.schema}`.`{object_name}`"

    def current_view_name(self, table_name: str) -> str:
        if table_name not in GOLD_TABLE_ARTIFACTS:
            raise ValueError(f"Unsupported Gold table name: {table_name}")
        return self.qualified_name(table_name)

    def history_table_name(self, table_name: str) -> str:
        if table_name not in GOLD_TABLE_ARTIFACTS:
            raise ValueError(f"Unsupported Gold table name: {table_name}")
        return self.qualified_name(f"{table_name}_history")

    def publication_table_name(self) -> str:
        return self.qualified_name(PUBLICATION_TABLE_NAME)


class DatabricksGoldAdapter:
    def __init__(self, spark: Any, config: DatabricksGoldConfig) -> None:
        self.spark = spark
        self.config = config

    def _validate_batch(
        self,
        snapshots: tuple[GoldSnapshotLoad, ...],
    ) -> tuple[str, datetime, str]:
        table_names = [snapshot.table_name for snapshot in snapshots]
        if len(table_names) != len(set(table_names)) or set(
            table_names
        ) != set(GOLD_TABLE_ARTIFACTS):
            raise ValueError(
                "Databricks publication requires all four Gold tables"
            )
        run_ids = {snapshot.run_id for snapshot in snapshots}
        run_started_values = {
            snapshot.run_started_at for snapshot in snapshots
        }
        video_ids = {snapshot.video_id for snapshot in snapshots}
        if (
            len(run_ids) != 1
            or len(run_started_values) != 1
            or len(video_ids) != 1
        ):
            raise ValueError(
                "Databricks publication requires one run and video_id"
            )
        return (
            next(iter(run_ids)),
            next(iter(run_started_values)),
            next(iter(video_ids)),
        )

    def _prepare_snapshot(self, snapshot: GoldSnapshotLoad) -> tuple[Any, int]:
        schema = SPARK_JSON_SCHEMAS[snapshot.table_name]
        dataframe = (
            self.spark.read.option("mode", "FAILFAST")
            .schema(schema)
            .json(snapshot.source_uri)
        )
        video_literal = _sql_string_literal(snapshot.video_id)
        version_literal = _sql_string_literal(
            snapshot.dictionary_version
        )
        invalid_lineage = dataframe.filter(
            f"NOT (video_id <=> {video_literal}) OR "
            f"NOT (dictionary_version <=> {version_literal})"
        ).limit(1).count()
        if invalid_lineage:
            raise ValueError(
                "Gold artifact lineage mismatch for table: "
                f"{snapshot.table_name}"
            )
        return dataframe, dataframe.count()

    def _write_history_snapshot(
        self,
        snapshot: GoldSnapshotLoad,
        dataframe: Any,
    ) -> None:
        run_literal = _sql_string_literal(snapshot.run_id)
        versioned_dataframe = dataframe.selectExpr(
            "*",
            f"{run_literal} AS load_run_id",
            "current_timestamp() AS loaded_at",
        )
        (
            versioned_dataframe.write.format("delta")
            .mode("overwrite")
            .option("replaceWhere", f"load_run_id = {run_literal}")
            .saveAsTable(
                self.config.history_table_name(snapshot.table_name)
            )
        )

    def _ensure_publication_table(self) -> None:
        self.spark.sql(
            f"""
            CREATE TABLE IF NOT EXISTS {self.config.publication_table_name()} (
                run_id STRING,
                video_id STRING,
                run_started_at TIMESTAMP,
                published_at TIMESTAMP,
                table_count BIGINT,
                total_row_count BIGINT,
                row_counts_json STRING
            ) USING DELTA
            """
        )

    def _read_published_counts(
        self,
        run_id: str,
        video_id: str,
    ) -> dict[str, int] | None:
        result = self.spark.sql(
            f"""
            SELECT row_counts_json
            FROM {self.config.publication_table_name()}
            WHERE run_id = {_sql_string_literal(run_id)}
              AND video_id = {_sql_string_literal(video_id)}
            LIMIT 1
            """
        ).first()
        if result is None:
            return None
        loaded_rows = json.loads(result[0])
        if (
            not isinstance(loaded_rows, dict)
            or set(loaded_rows) != set(GOLD_TABLE_ARTIFACTS)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in loaded_rows.values()
            )
        ):
            raise ValueError("Published Gold row counts are invalid")
        return loaded_rows

    def _ensure_current_views(self) -> None:
        publication_table = self.config.publication_table_name()
        for table_name, schema in SPARK_JSON_SCHEMAS.items():
            columns = ",\n                    ".join(
                f"history.`{column}`"
                for column in _schema_column_names(schema)
            )
            self.spark.sql(
                f"""
                CREATE OR REPLACE VIEW {self.config.current_view_name(table_name)} AS
                WITH latest_publication AS (
                    SELECT video_id, run_id
                    FROM (
                        SELECT
                            video_id,
                            run_id,
                            ROW_NUMBER() OVER (
                                PARTITION BY video_id
                                ORDER BY
                                    run_started_at DESC,
                                    published_at DESC,
                                    run_id DESC
                            ) AS publication_rank
                        FROM {publication_table}
                    )
                    WHERE publication_rank = 1
                )
                SELECT
                    {columns}
                FROM {self.config.history_table_name(table_name)} AS history
                INNER JOIN latest_publication AS publication
                    ON history.video_id = publication.video_id
                   AND history.load_run_id = publication.run_id
                """
            )

    def _publish_run(
        self,
        run_id: str,
        run_started_at: datetime,
        video_id: str,
        loaded_rows: dict[str, int],
    ) -> None:
        run_literal = _sql_string_literal(run_id)
        video_literal = _sql_string_literal(video_id)
        started_at_utc = run_started_at.astimezone(timezone.utc)
        started_at_literal = started_at_utc.replace(
            tzinfo=None
        ).isoformat(sep=" ")
        total_row_count = sum(loaded_rows.values())
        row_counts_literal = _sql_string_literal(
            json.dumps(loaded_rows, sort_keys=True)
        )
        self.spark.sql(
            f"""
            MERGE INTO {self.config.publication_table_name()} AS target
            USING (
                SELECT
                    {run_literal} AS run_id,
                    {video_literal} AS video_id,
                    TIMESTAMP '{started_at_literal}' AS run_started_at,
                    current_timestamp() AS published_at,
                    {len(loaded_rows)} AS table_count,
                    {total_row_count} AS total_row_count,
                    {row_counts_literal} AS row_counts_json
            ) AS source
            ON target.run_id = source.run_id
           AND target.video_id = source.video_id
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
            """
        )

    def load_snapshots(
        self,
        snapshots: tuple[GoldSnapshotLoad, ...],
    ) -> dict[str, int]:
        run_id, run_started_at, video_id = self._validate_batch(snapshots)
        self._ensure_publication_table()
        published_counts = self._read_published_counts(run_id, video_id)
        if published_counts is not None:
            self._ensure_current_views()
            return published_counts
        prepared = [
            (snapshot, *self._prepare_snapshot(snapshot))
            for snapshot in snapshots
        ]
        for snapshot, dataframe, _ in prepared:
            self._write_history_snapshot(snapshot, dataframe)
        loaded_rows = {
            snapshot.table_name: row_count
            for snapshot, _, row_count in prepared
        }
        self._ensure_current_views()
        self._publish_run(
            run_id,
            run_started_at,
            video_id,
            loaded_rows,
        )
        return loaded_rows
