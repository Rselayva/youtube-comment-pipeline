import json
from datetime import datetime, timezone
from unittest.mock import Mock, call

import pytest

from transformation.entity_sov_metrics import (
    DAILY_ENTITY_SOV_SCHEMA,
    VIDEO_ENTITY_SOV_SCHEMA,
)
from transformation.topic_metrics import (
    DAILY_TOPIC_METRICS_SCHEMA,
    VIDEO_TOPIC_METRICS_SCHEMA,
)
from warehouse.databricks_adapter import (
    SPARK_JSON_SCHEMAS,
    DatabricksGoldAdapter,
    DatabricksGoldConfig,
)
from warehouse.gold_load_contract import GoldSnapshotLoad


VIDEO_ID = "aFrQIJ5cbRc"
RUN_ID = f"{VIDEO_ID}_20260821T120000000000Z"


def make_snapshot(
    table_name: str,
    dictionary_version: str,
    run_id: str = RUN_ID,
) -> GoldSnapshotLoad:
    return GoldSnapshotLoad(
        table_name=table_name,
        source_uri=(
            f"/Volumes/audience/prod/gold/{table_name}.jsonl"
        ),
        run_id=run_id,
        run_started_at=datetime(
            2026,
            8,
            21,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        video_id=VIDEO_ID,
        dictionary_version=dictionary_version,
    )


def make_all_snapshots(run_id: str = RUN_ID):
    return (
        make_snapshot("gold_video_entity_sov", "nmixx_v2", run_id),
        make_snapshot("gold_daily_entity_sov", "nmixx_v2", run_id),
        make_snapshot(
            "gold_video_topic_metrics",
            "comment_topics_v1",
            run_id,
        ),
        make_snapshot(
            "gold_daily_topic_metrics",
            "comment_topics_v1",
            run_id,
        ),
    )


def make_dataframe(row_count: int = 1, invalid_lineage: int = 0):
    dataframe = Mock()
    filtered = Mock()
    limited = Mock()
    dataframe.filter.return_value = filtered
    filtered.limit.return_value = limited
    limited.count.return_value = invalid_lineage
    dataframe.count.return_value = row_count

    versioned_dataframe = Mock()
    writer = Mock()
    versioned_dataframe.write = writer
    writer.format.return_value = writer
    writer.mode.return_value = writer
    writer.option.return_value = writer
    dataframe.selectExpr.return_value = versioned_dataframe
    return dataframe, writer


def make_spark(dataframes):
    spark = Mock()
    reader = Mock()
    spark.read = reader
    reader.option.return_value = reader
    reader.schema.return_value = reader
    reader.json.side_effect = dataframes
    return spark, reader


def configure_unpublished_run(spark, events=None):
    def execute_sql(sql):
        if events is not None:
            events.append(
                "publish" if "MERGE INTO" in sql else "metadata"
            )
        if "SELECT row_counts_json" in sql:
            result = Mock()
            result.first.return_value = None
            return result
        return None

    spark.sql.side_effect = execute_sql


def parse_spark_ddl_schema(schema: str) -> dict[str, str]:
    return {
        parts[0]: parts[1]
        for line in schema.splitlines()
        if (parts := line.strip().rstrip(",").split())
    }


def test_databricks_schemas_match_platform_neutral_gold_schemas():
    assert {
        table_name: parse_spark_ddl_schema(schema)
        for table_name, schema in SPARK_JSON_SCHEMAS.items()
    } == {
        "gold_video_entity_sov": VIDEO_ENTITY_SOV_SCHEMA,
        "gold_daily_entity_sov": DAILY_ENTITY_SOV_SCHEMA,
        "gold_video_topic_metrics": VIDEO_TOPIC_METRICS_SCHEMA,
        "gold_daily_topic_metrics": DAILY_TOPIC_METRICS_SCHEMA,
    }


def test_databricks_adapter_publishes_versioned_gold_views_last():
    snapshots = make_all_snapshots()
    rows = [7, 14, 3, 6]
    dataframes_and_writers = [make_dataframe(count) for count in rows]
    dataframes = [item[0] for item in dataframes_and_writers]
    spark, reader = make_spark(dataframes)
    events = []
    for _, writer in dataframes_and_writers:
        writer.saveAsTable.side_effect = (
            lambda _table, events=events: events.append("history_write")
        )

    configure_unpublished_run(spark, events)
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    loaded_rows = adapter.load_snapshots(snapshots)

    assert loaded_rows == dict(zip(SPARK_JSON_SCHEMAS, rows))
    assert reader.json.call_args_list == [
        call(snapshot.source_uri) for snapshot in snapshots
    ]
    first_dataframe, first_writer = dataframes_and_writers[0]
    first_dataframe.selectExpr.assert_called_once_with(
        "*",
        f"'{RUN_ID}' AS load_run_id",
        "current_timestamp() AS loaded_at",
    )
    first_writer.option.assert_called_once_with(
        "replaceWhere",
        f"load_run_id = '{RUN_ID}'",
    )
    first_writer.saveAsTable.assert_called_once_with(
        "`audience`.`gold`.`gold_video_entity_sov_history`"
    )
    sql_statements = [item.args[0] for item in spark.sql.call_args_list]
    assert "CREATE TABLE IF NOT EXISTS" in sql_statements[0]
    view_sql = next(
        sql for sql in sql_statements if "CREATE OR REPLACE VIEW" in sql
    )
    assert "gold_video_entity_sov_history" in view_sql
    assert "gold_load_publications" in view_sql
    assert "MERGE INTO" in sql_statements[-1]
    assert RUN_ID in sql_statements[-1]
    assert "row_counts_json" in sql_statements[-1]
    assert "ORDER BY\n                                    run_started_at DESC" in (
        view_sql
    )
    assert events[-1] == "publish"


def test_databricks_adapter_preflights_all_sources_before_writing():
    items = [make_dataframe() for _ in range(4)]
    items[2][0].filter.return_value.limit.return_value.count.return_value = 1
    spark, _ = make_spark([item[0] for item in items])
    configure_unpublished_run(spark)
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    with pytest.raises(ValueError, match="artifact lineage mismatch"):
        adapter.load_snapshots(make_all_snapshots())

    for _, writer in items:
        writer.format.assert_not_called()
    assert all(
        "MERGE INTO" not in item.args[0]
        for item in spark.sql.call_args_list
    )


def test_databricks_adapter_rejects_corrupt_published_counts():
    spark, _ = make_spark([])

    def execute_sql(sql):
        if "SELECT row_counts_json" in sql:
            result = Mock()
            result.first.return_value = [json.dumps({"one_table": 1})]
            return result
        return None

    spark.sql.side_effect = execute_sql
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    with pytest.raises(
        ValueError,
        match="Published Gold row counts are invalid",
    ):
        adapter.load_snapshots(make_all_snapshots())


def test_databricks_adapter_does_not_publish_after_history_write_failure():
    items = [make_dataframe() for _ in range(4)]
    items[2][1].saveAsTable.side_effect = RuntimeError("write failed")
    spark, _ = make_spark([item[0] for item in items])
    configure_unpublished_run(spark)
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    with pytest.raises(RuntimeError, match="write failed"):
        adapter.load_snapshots(make_all_snapshots())

    assert all(
        "MERGE INTO" not in item.args[0]
        for item in spark.sql.call_args_list
    )


def test_databricks_adapter_skips_immutable_published_run():
    published_counts = {
        "gold_video_entity_sov": 7,
        "gold_daily_entity_sov": 14,
        "gold_video_topic_metrics": 3,
        "gold_daily_topic_metrics": 6,
    }
    spark, reader = make_spark([])

    def execute_sql(sql):
        if "SELECT row_counts_json" in sql:
            result = Mock()
            result.first.return_value = [json.dumps(published_counts)]
            return result
        return None

    spark.sql.side_effect = execute_sql
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    loaded_rows = adapter.load_snapshots(make_all_snapshots())

    assert loaded_rows == published_counts
    reader.option.assert_not_called()
    assert all(
        "MERGE INTO" not in item.args[0]
        for item in spark.sql.call_args_list
    )


def test_databricks_adapter_requires_complete_single_run_batch():
    dataframe, _ = make_dataframe()
    spark, _ = make_spark([dataframe])
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    with pytest.raises(
        ValueError,
        match="requires all four Gold tables",
    ):
        adapter.load_snapshots(make_all_snapshots()[:1])

    spark.read.option.assert_not_called()


@pytest.mark.parametrize(
    ("field_name", "catalog", "schema"),
    [
        ("catalog", "bad-name", "gold"),
        ("schema", "audience", "gold;drop"),
    ],
)
def test_databricks_config_rejects_unsafe_identifiers(
    field_name,
    catalog,
    schema,
):
    with pytest.raises(
        ValueError,
        match=f"{field_name} must be a valid Unity Catalog identifier",
    ):
        DatabricksGoldConfig(catalog=catalog, schema=schema)


def test_databricks_adapter_escapes_run_id_in_history_predicate():
    dataframe, writer = make_dataframe()
    adapter = DatabricksGoldAdapter(
        Mock(),
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )
    snapshot = make_snapshot(
        "gold_video_entity_sov",
        "nmixx_v2",
        run_id="run'id",
    )

    adapter._write_history_snapshot(snapshot, dataframe)

    writer.option.assert_called_once_with(
        "replaceWhere",
        "load_run_id = 'run''id'",
    )
