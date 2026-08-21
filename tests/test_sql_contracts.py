import re
import sqlite3
from pathlib import Path

from transformation.entity_sov_metrics import (
    DAILY_ENTITY_SOV_SCHEMA,
    VIDEO_ENTITY_SOV_SCHEMA,
)
from transformation.topic_metrics import (
    DAILY_TOPIC_METRICS_SCHEMA,
    VIDEO_TOPIC_METRICS_SCHEMA,
)


SQL_SCHEMA_PATH = Path("sql/gold_schema.sql")
SQL_TYPE_BY_SCHEMA_TYPE = {
    "STRING": "VARCHAR",
    "BIGINT": "BIGINT",
    "DOUBLE": "DOUBLE",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
}


def parse_table_columns(sql_text: str) -> dict[str, tuple[str, ...]]:
    table_columns = {}
    table_pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);",
        re.DOTALL,
    )

    for table_name, raw_columns in table_pattern.findall(sql_text):
        columns = tuple(
            line.strip().split()[0]
            for line in raw_columns.splitlines()
            if line.strip()
        )
        table_columns[table_name] = columns

    return table_columns


def parse_table_column_types(
    sql_text: str,
) -> dict[str, dict[str, str]]:
    table_column_types = {}
    table_pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);",
        re.DOTALL,
    )

    for table_name, raw_columns in table_pattern.findall(sql_text):
        table_column_types[table_name] = {
            parts[0]: parts[1]
            for line in raw_columns.splitlines()
            if (parts := line.strip().rstrip(",").split())
        }

    return table_column_types


def test_gold_sql_contract_columns_match_python_schemas():
    table_columns = parse_table_columns(
        SQL_SCHEMA_PATH.read_text(encoding="utf-8")
    )

    assert table_columns == {
        "gold_video_entity_sov": tuple(VIDEO_ENTITY_SOV_SCHEMA),
        "gold_daily_entity_sov": tuple(DAILY_ENTITY_SOV_SCHEMA),
        "gold_video_topic_metrics": tuple(VIDEO_TOPIC_METRICS_SCHEMA),
        "gold_daily_topic_metrics": tuple(DAILY_TOPIC_METRICS_SCHEMA),
    }


def test_gold_sql_contract_types_match_python_schemas():
    table_column_types = parse_table_column_types(
        SQL_SCHEMA_PATH.read_text(encoding="utf-8")
    )
    schemas_by_table = {
        "gold_video_entity_sov": VIDEO_ENTITY_SOV_SCHEMA,
        "gold_daily_entity_sov": DAILY_ENTITY_SOV_SCHEMA,
        "gold_video_topic_metrics": VIDEO_TOPIC_METRICS_SCHEMA,
        "gold_daily_topic_metrics": DAILY_TOPIC_METRICS_SCHEMA,
    }

    assert table_column_types == {
        table_name: {
            column_name: SQL_TYPE_BY_SCHEMA_TYPE[schema_type]
            for column_name, schema_type in schema.items()
        }
        for table_name, schema in schemas_by_table.items()
    }


def test_sql_examples_only_reference_declared_gold_tables():
    declared_tables = set(
        parse_table_columns(
            SQL_SCHEMA_PATH.read_text(encoding="utf-8")
        )
    )
    query_text = Path("sql/example_queries.sql").read_text(
        encoding="utf-8"
    )
    referenced_tables = set(
        re.findall(r"\bFROM\s+(gold_\w+)", query_text, re.IGNORECASE)
    )

    assert referenced_tables
    assert referenced_tables <= declared_tables


def test_gold_schema_and_example_queries_are_executable_sql():
    schema_sql = SQL_SCHEMA_PATH.read_text(encoding="utf-8")
    example_sql = Path("sql/example_queries.sql").read_text(
        encoding="utf-8"
    )

    with sqlite3.connect(":memory:") as connection:
        connection.executescript(schema_sql)
        connection.executescript(example_sql)

        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert table_names == {
        "gold_video_entity_sov",
        "gold_daily_entity_sov",
        "gold_video_topic_metrics",
        "gold_daily_topic_metrics",
    }
