import math
from collections import defaultdict
from datetime import date, datetime

from transformation.entity_sov_metrics import (
    DAILY_ENTITY_SOV_SCHEMA,
    VIDEO_ENTITY_SOV_SCHEMA,
)
from transformation.topic_metrics import (
    DAILY_TOPIC_METRICS_SCHEMA,
    VIDEO_TOPIC_METRICS_SCHEMA,
)


def _validate_schema(metric: dict, schema: dict, dataset_name: str) -> None:
    expected_fields = set(schema)
    actual_fields = set(metric)
    if actual_fields != expected_fields:
        missing_fields = sorted(expected_fields - actual_fields)
        extra_fields = sorted(actual_fields - expected_fields)
        raise ValueError(
            f"{dataset_name} schema mismatch: missing={missing_fields} "
            f"extra={extra_fields}"
        )


def _validate_non_empty_string(value, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_count(value, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _validate_ratio(value, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")


def _validate_timestamp(value, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field_name} must be timezone-aware")


def _validate_expected_ratio(
    actual: float,
    numerator: int,
    denominator: int,
    field_name: str,
) -> None:
    expected = numerator / denominator if denominator else 0.0
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(
            f"{field_name} does not match its numerator and denominator"
        )


def _validate_group_totals(
    grouped_metrics: dict[tuple, list[dict]],
    count_field: str,
    total_field: str,
    share_field: str,
) -> None:
    for metrics in grouped_metrics.values():
        totals = {metric[total_field] for metric in metrics}
        if len(totals) != 1:
            raise ValueError(f"{total_field} must be consistent per group")

        declared_total = next(iter(totals))
        calculated_total = sum(metric[count_field] for metric in metrics)
        if declared_total != calculated_total:
            raise ValueError(
                f"{total_field} does not equal grouped {count_field}"
            )

        expected_share_total = 1.0 if declared_total else 0.0
        actual_share_total = sum(metric[share_field] for metric in metrics)
        if not math.isclose(
            actual_share_total,
            expected_share_total,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(f"{share_field} does not sum correctly")


def _validate_snapshot_consistency(
    grouped_metrics: dict[tuple, list[dict]],
) -> None:
    for metrics in grouped_metrics.values():
        if len({metric["comment_count"] for metric in metrics}) != 1:
            raise ValueError("comment_count must be consistent per snapshot")
        if len({metric["snapshot_at"] for metric in metrics}) != 1:
            raise ValueError("snapshot_at must be consistent per snapshot")


def validate_entity_sov_metrics(
    metrics: list[dict],
    daily: bool = False,
    expected_video_id: str | None = None,
    expected_dictionary_version: str | None = None,
) -> None:
    schema = DAILY_ENTITY_SOV_SCHEMA if daily else VIDEO_ENTITY_SOV_SCHEMA
    dataset_name = "daily entity SOV" if daily else "video entity SOV"
    logical_keys = set()
    grouped_metrics = defaultdict(list)
    snapshot_metrics = defaultdict(list)

    for metric in metrics:
        _validate_schema(metric, schema, dataset_name)
        for field_name in (
            "video_id",
            "entity_type",
            "entity_id",
            "group_id",
            "canonical_name",
            "dictionary_version",
        ):
            _validate_non_empty_string(metric[field_name], field_name)
        if metric["entity_type"] not in {"group", "member"}:
            raise ValueError("entity_type must be group or member")
        if (
            expected_video_id is not None
            and metric["video_id"] != expected_video_id
        ):
            raise ValueError("metric video_id does not match output path")
        if (
            expected_dictionary_version is not None
            and metric["dictionary_version"]
            != expected_dictionary_version
        ):
            raise ValueError(
                "metric dictionary_version does not match output path"
            )

        for field_name in (
            "comment_count",
            "mention_comment_count",
            "entity_type_mention_comment_count",
        ):
            _validate_count(metric[field_name], field_name)
        if metric["comment_count"] == 0:
            raise ValueError("non-empty Gold metrics require comments")
        if metric["mention_comment_count"] > metric["comment_count"]:
            raise ValueError("mention_comment_count exceeds comment_count")

        for field_name in (
            "comment_share_of_voice",
            "entity_share_of_voice",
        ):
            _validate_ratio(metric[field_name], field_name)
        _validate_expected_ratio(
            metric["comment_share_of_voice"],
            metric["mention_comment_count"],
            metric["comment_count"],
            "comment_share_of_voice",
        )
        _validate_expected_ratio(
            metric["entity_share_of_voice"],
            metric["mention_comment_count"],
            metric["entity_type_mention_comment_count"],
            "entity_share_of_voice",
        )
        _validate_timestamp(metric["snapshot_at"], "snapshot_at")

        date_key = None
        if daily:
            if not isinstance(metric["comment_date"], date) or isinstance(
                metric["comment_date"], datetime
            ):
                raise ValueError("comment_date must be a date")
            date_key = metric["comment_date"]

        logical_key = (
            metric["video_id"],
            date_key,
            metric["dictionary_version"],
            metric["entity_type"],
            metric["entity_id"],
        )
        if logical_key in logical_keys:
            raise ValueError("Duplicate entity SOV logical key")
        logical_keys.add(logical_key)

        group_key = (
            metric["video_id"],
            date_key,
            metric["dictionary_version"],
            metric["entity_type"],
        )
        grouped_metrics[group_key].append(metric)
        snapshot_metrics[group_key[:-1]].append(metric)

    _validate_group_totals(
        grouped_metrics,
        "mention_comment_count",
        "entity_type_mention_comment_count",
        "entity_share_of_voice",
    )
    _validate_snapshot_consistency(snapshot_metrics)


def validate_topic_metrics(
    metrics: list[dict],
    daily: bool = False,
    expected_video_id: str | None = None,
    expected_dictionary_version: str | None = None,
) -> None:
    schema = DAILY_TOPIC_METRICS_SCHEMA if daily else VIDEO_TOPIC_METRICS_SCHEMA
    dataset_name = "daily topic metrics" if daily else "video topic metrics"
    logical_keys = set()
    grouped_metrics = defaultdict(list)

    for metric in metrics:
        _validate_schema(metric, schema, dataset_name)
        for field_name in (
            "video_id",
            "topic_id",
            "display_name",
            "dictionary_version",
        ):
            _validate_non_empty_string(metric[field_name], field_name)
        if (
            expected_video_id is not None
            and metric["video_id"] != expected_video_id
        ):
            raise ValueError("metric video_id does not match output path")
        if (
            expected_dictionary_version is not None
            and metric["dictionary_version"]
            != expected_dictionary_version
        ):
            raise ValueError(
                "metric dictionary_version does not match output path"
            )

        for field_name in (
            "comment_count",
            "topic_comment_count",
            "topic_comment_count_total",
        ):
            _validate_count(metric[field_name], field_name)
        if metric["comment_count"] == 0:
            raise ValueError("non-empty Gold metrics require comments")
        if metric["topic_comment_count"] > metric["comment_count"]:
            raise ValueError("topic_comment_count exceeds comment_count")

        for field_name in (
            "comment_share_of_voice",
            "topic_share_of_voice",
        ):
            _validate_ratio(metric[field_name], field_name)
        _validate_expected_ratio(
            metric["comment_share_of_voice"],
            metric["topic_comment_count"],
            metric["comment_count"],
            "comment_share_of_voice",
        )
        _validate_expected_ratio(
            metric["topic_share_of_voice"],
            metric["topic_comment_count"],
            metric["topic_comment_count_total"],
            "topic_share_of_voice",
        )
        _validate_timestamp(metric["snapshot_at"], "snapshot_at")

        date_key = None
        if daily:
            if not isinstance(metric["comment_date"], date) or isinstance(
                metric["comment_date"], datetime
            ):
                raise ValueError("comment_date must be a date")
            date_key = metric["comment_date"]

        logical_key = (
            metric["video_id"],
            date_key,
            metric["dictionary_version"],
            metric["topic_id"],
        )
        if logical_key in logical_keys:
            raise ValueError("Duplicate topic metrics logical key")
        logical_keys.add(logical_key)

        group_key = (
            metric["video_id"],
            date_key,
            metric["dictionary_version"],
        )
        grouped_metrics[group_key].append(metric)

    _validate_group_totals(
        grouped_metrics,
        "topic_comment_count",
        "topic_comment_count_total",
        "topic_share_of_voice",
    )
    _validate_snapshot_consistency(grouped_metrics)
