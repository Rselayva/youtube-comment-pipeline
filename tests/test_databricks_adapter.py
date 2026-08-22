from unittest.mock import Mock, call

import pytest

from warehouse.databricks_adapter import (
    SPARK_JSON_SCHEMAS,
    DatabricksGoldAdapter,
    DatabricksGoldConfig,
)
from warehouse.gold_load_contract import GoldSnapshotLoad
from transformation.entity_sov_metrics import (
    DAILY_ENTITY_SOV_SCHEMA,
    VIDEO_ENTITY_SOV_SCHEMA,
)
from transformation.topic_metrics import (
    DAILY_TOPIC_METRICS_SCHEMA,
    VIDEO_TOPIC_METRICS_SCHEMA,
)


VIDEO_ID = "aFrQIJ5cbRc"


def make_snapshot(
    table_name: str = "gold_video_entity_sov",
    dictionary_version: str = "nmixx_v2",
) -> GoldSnapshotLoad:
    return GoldSnapshotLoad(
        table_name=table_name,
        source_uri=(
            f"/Volumes/audience/prod/gold/{table_name}.jsonl"
        ),
        video_id=VIDEO_ID,
        dictionary_version=dictionary_version,
    )


def make_dataframe(row_count: int = 1, invalid_lineage: int = 0):
    dataframe = Mock()
    filtered = Mock()
    limited = Mock()
    dataframe.filter.return_value = filtered
    filtered.limit.return_value = limited
    limited.count.return_value = invalid_lineage
    dataframe.count.return_value = row_count
    writer = Mock()
    dataframe.write = writer
    writer.format.return_value = writer
    writer.mode.return_value = writer
    writer.option.return_value = writer
    return dataframe, writer


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


def test_databricks_adapter_loads_delta_tables_with_replace_where():
    snapshots = (
        make_snapshot(),
        make_snapshot(
            "gold_video_topic_metrics",
            "comment_topics_v1",
        ),
    )
    dataframes_and_writers = [make_dataframe(7), make_dataframe(3)]
    dataframes = [item[0] for item in dataframes_and_writers]
    spark = Mock()
    reader = Mock()
    spark.read = reader
    reader.option.return_value = reader
    reader.schema.return_value = reader
    reader.json.side_effect = dataframes
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    loaded_rows = adapter.load_snapshots(snapshots)

    assert loaded_rows == {
        "gold_video_entity_sov": 7,
        "gold_video_topic_metrics": 3,
    }
    assert reader.option.call_args_list == [
        call("mode", "FAILFAST"),
        call("mode", "FAILFAST"),
    ]
    assert reader.schema.call_args_list == [
        call(SPARK_JSON_SCHEMAS[snapshot.table_name])
        for snapshot in snapshots
    ]
    assert reader.json.call_args_list == [
        call(snapshot.source_uri) for snapshot in snapshots
    ]
    first_writer = dataframes_and_writers[0][1]
    first_writer.format.assert_called_once_with("delta")
    first_writer.mode.assert_called_once_with("overwrite")
    first_writer.option.assert_called_once_with(
        "replaceWhere",
        f"video_id = '{VIDEO_ID}' AND "
        "dictionary_version = 'nmixx_v2'",
    )
    first_writer.saveAsTable.assert_called_once_with(
        "`audience`.`gold`.`gold_video_entity_sov`"
    )


def test_databricks_adapter_rejects_lineage_mismatch_before_write():
    dataframe, writer = make_dataframe(invalid_lineage=1)
    spark = Mock()
    spark.read.option.return_value.schema.return_value.json.return_value = (
        dataframe
    )
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )

    with pytest.raises(ValueError, match="artifact lineage mismatch"):
        adapter.load_snapshots((make_snapshot(),))

    writer.format.assert_not_called()


def test_databricks_adapter_preflights_all_sources_before_writing():
    valid_dataframe, valid_writer = make_dataframe()
    invalid_dataframe, invalid_writer = make_dataframe(
        invalid_lineage=1
    )
    spark = Mock()
    reader = Mock()
    spark.read = reader
    reader.option.return_value = reader
    reader.schema.return_value = reader
    reader.json.side_effect = [valid_dataframe, invalid_dataframe]
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )
    snapshots = (
        make_snapshot(),
        make_snapshot(
            "gold_video_topic_metrics",
            "comment_topics_v1",
        ),
    )

    with pytest.raises(ValueError, match="artifact lineage mismatch"):
        adapter.load_snapshots(snapshots)

    valid_writer.format.assert_not_called()
    invalid_writer.format.assert_not_called()


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


def test_databricks_adapter_escapes_replace_where_values():
    dataframe, writer = make_dataframe()
    spark = Mock()
    spark.read.option.return_value.schema.return_value.json.return_value = (
        dataframe
    )
    adapter = DatabricksGoldAdapter(
        spark,
        DatabricksGoldConfig(catalog="audience", schema="gold"),
    )
    snapshot = make_snapshot(dictionary_version="topic's_v1")

    adapter.load_snapshots((snapshot,))

    writer.option.assert_called_once_with(
        "replaceWhere",
        f"video_id = '{VIDEO_ID}' AND "
        "dictionary_version = 'topic''s_v1'",
    )
