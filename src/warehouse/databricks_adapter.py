import re
from dataclasses import dataclass
from typing import Any

from warehouse.gold_load_contract import (
    GOLD_TABLE_ARTIFACTS,
    GoldSnapshotLoad,
)


UNITY_CATALOG_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

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


@dataclass(frozen=True)
class DatabricksGoldConfig:
    catalog: str
    schema: str

    def __post_init__(self) -> None:
        _validate_identifier(self.catalog, "catalog")
        _validate_identifier(self.schema, "schema")

    def qualified_table_name(self, table_name: str) -> str:
        if table_name not in GOLD_TABLE_ARTIFACTS:
            raise ValueError(f"Unsupported Gold table name: {table_name}")
        return f"`{self.catalog}`.`{self.schema}`.`{table_name}`"


class DatabricksGoldAdapter:
    def __init__(self, spark: Any, config: DatabricksGoldConfig) -> None:
        self.spark = spark
        self.config = config

    def _prepare_snapshot(self, snapshot: GoldSnapshotLoad) -> tuple[Any, int]:
        schema = SPARK_JSON_SCHEMAS.get(snapshot.table_name)
        if schema is None:
            raise ValueError(
                f"Unsupported Gold table name: {snapshot.table_name}"
            )

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

    def _write_snapshot(
        self,
        snapshot: GoldSnapshotLoad,
        dataframe: Any,
    ) -> None:
        video_literal = _sql_string_literal(snapshot.video_id)
        version_literal = _sql_string_literal(
            snapshot.dictionary_version
        )
        replace_where = (
            f"video_id = {video_literal} AND "
            f"dictionary_version = {version_literal}"
        )
        (
            dataframe.write.format("delta")
            .mode("overwrite")
            .option("replaceWhere", replace_where)
            .saveAsTable(
                self.config.qualified_table_name(snapshot.table_name)
            )
        )

    def load_snapshots(
        self,
        snapshots: tuple[GoldSnapshotLoad, ...],
    ) -> dict[str, int]:
        prepared = [
            (snapshot, *self._prepare_snapshot(snapshot))
            for snapshot in snapshots
        ]
        for snapshot, dataframe, _ in prepared:
            self._write_snapshot(snapshot, dataframe)
        return {
            snapshot.table_name: row_count
            for snapshot, _, row_count in prepared
        }
