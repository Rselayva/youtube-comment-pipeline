import json

import pytest

from warehouse.databricks_validation import (
    validate_latest_gold_publication,
)
from warehouse.gold_load_contract import GOLD_TABLE_ARTIFACTS


VIDEO_ID = "aFrQIJ5cbRc"


class QueryResult:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class SparkSequence:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.queries = []

    def sql(self, query):
        self.queries.append(query)
        return QueryResult(next(self.rows))


def test_validate_latest_gold_publication_reconciles_all_tables():
    expected = {
        table_name: index
        for index, table_name in enumerate(GOLD_TABLE_ARTIFACTS, start=1)
    }
    count_rows = [
        (expected[table_name],)
        for table_name in GOLD_TABLE_ARTIFACTS
        for _ in range(2)
    ]
    spark = SparkSequence(
        [
            (
                "run-123",
                4,
                sum(expected.values()),
                json.dumps(expected),
            ),
            *count_rows,
        ]
    )

    result = validate_latest_gold_publication(
        video_id=VIDEO_ID,
        spark=spark,
        catalog="audience",
        schema="gold",
    )

    assert result["status"] == "passed"
    assert result["run_id"] == "run-123"
    assert result["current_rows"] == expected
    assert result["history_rows"] == expected
    assert len(spark.queries) == 9


def test_validate_latest_gold_publication_rejects_missing_publication():
    with pytest.raises(ValueError, match="No published Gold run"):
        validate_latest_gold_publication(
            video_id=VIDEO_ID,
            spark=SparkSequence([None]),
            catalog="audience",
            schema="gold",
        )


def test_validate_latest_gold_publication_rejects_count_mismatch():
    expected = {table_name: 1 for table_name in GOLD_TABLE_ARTIFACTS}
    spark = SparkSequence(
        [
            ("run-123", 4, 4, json.dumps(expected)),
            (0,),
            (1,),
        ]
    )

    with pytest.raises(ValueError, match="Current view row count mismatch"):
        validate_latest_gold_publication(
            video_id=VIDEO_ID,
            spark=spark,
            catalog="audience",
            schema="gold",
        )


def test_validate_latest_gold_publication_rejects_invalid_audit_json():
    spark = SparkSequence([("run-123", 4, 4, "not-json")])

    with pytest.raises(ValueError, match="row counts are invalid"):
        validate_latest_gold_publication(
            video_id=VIDEO_ID,
            spark=spark,
            catalog="audience",
            schema="gold",
        )
