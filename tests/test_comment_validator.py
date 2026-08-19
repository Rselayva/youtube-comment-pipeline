from datetime import datetime, timezone

import pytest

from validation.comment_validator import (
    validate_comment_dataset,
    validate_comment_record,
)


VALID_COMMENT = {
    "comment_id": "comment-1",
    "video_id": "video-1",
    "comment_text": "Test comment",
    "published_at": datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc),
    "updated_at": datetime(2026, 8, 18, 9, 0, tzinfo=timezone.utc),
    "ingested_at": datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc),
    "like_count": 0,
    "total_reply_count": 0,
}


def test_validate_comment_record_accepts_required_fields():
    validation_errors = validate_comment_record(VALID_COMMENT)

    assert validation_errors == []


def test_validate_comment_record_reports_all_missing_required_fields():
    comment = VALID_COMMENT.copy()
    comment["comment_id"] = None
    comment.pop("published_at")

    validation_errors = validate_comment_record(comment)

    assert validation_errors == [
        "comment_id is required",
        "published_at is required",
    ]


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_error"),
    [
        ("like_count", -1, "like_count must be non-negative"),
        (
            "total_reply_count",
            -1,
            "total_reply_count must be non-negative",
        ),
        ("like_count", 1.5, "like_count must be an integer"),
        (
            "total_reply_count",
            True,
            "total_reply_count must be an integer",
        ),
    ],
)
def test_validate_comment_record_rejects_invalid_count(
    field_name,
    invalid_value,
    expected_error,
):
    comment = VALID_COMMENT.copy()
    comment[field_name] = invalid_value

    validation_errors = validate_comment_record(comment)

    assert validation_errors == [expected_error]


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_error"),
    [
        (
            "published_at",
            "2026-08-18T08:00:00Z",
            "published_at must be a datetime",
        ),
        (
            "updated_at",
            datetime(2026, 8, 18, 9, 0),
            "updated_at must include timezone information",
        ),
    ],
)
def test_validate_comment_record_rejects_invalid_timestamp(
    field_name,
    invalid_value,
    expected_error,
):
    comment = VALID_COMMENT.copy()
    comment[field_name] = invalid_value

    validation_errors = validate_comment_record(comment)

    assert validation_errors == [expected_error]


@pytest.mark.parametrize(
    ("published_at", "updated_at", "ingested_at", "expected_error"),
    [
        (
            datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 18, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc),
            "published_at must not be after updated_at",
        ),
        (
            datetime(2026, 8, 18, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 19, 9, 0, tzinfo=timezone.utc),
            datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc),
            "updated_at must not be after ingested_at",
        ),
    ],
)
def test_validate_comment_record_rejects_invalid_timestamp_order(
    published_at,
    updated_at,
    ingested_at,
    expected_error,
):
    comment = VALID_COMMENT.copy()
    comment["published_at"] = published_at
    comment["updated_at"] = updated_at
    comment["ingested_at"] = ingested_at

    validation_errors = validate_comment_record(comment)

    assert validation_errors == [expected_error]


def test_validate_comment_dataset_splits_valid_and_invalid_records():
    valid_comment = VALID_COMMENT.copy()
    invalid_comment = VALID_COMMENT.copy()
    invalid_comment["comment_id"] = "comment-2"
    invalid_comment["like_count"] = -1

    valid_records, rejected_records = validate_comment_dataset(
        [valid_comment, invalid_comment]
    )

    assert valid_records == [valid_comment]
    assert rejected_records == [
        {
            **invalid_comment,
            "validation_errors": ["like_count must be non-negative"],
        }
    ]


def test_validate_comment_dataset_rejects_all_duplicate_comment_ids():
    first_duplicate = VALID_COMMENT.copy()
    second_duplicate = VALID_COMMENT.copy()
    second_duplicate["comment_text"] = "Updated test comment"

    valid_records, rejected_records = validate_comment_dataset(
        [first_duplicate, second_duplicate]
    )

    assert valid_records == []
    assert rejected_records == [
        {
            **first_duplicate,
            "validation_errors": [
                "comment_id must be unique within the batch"
            ],
        },
        {
            **second_duplicate,
            "validation_errors": [
                "comment_id must be unique within the batch"
            ],
        },
    ]


def test_validate_comment_dataset_combines_record_and_duplicate_errors():
    first_duplicate = VALID_COMMENT.copy()
    first_duplicate["like_count"] = -1
    second_duplicate = VALID_COMMENT.copy()

    _, rejected_records = validate_comment_dataset(
        [first_duplicate, second_duplicate]
    )

    assert rejected_records[0]["validation_errors"] == [
        "like_count must be non-negative",
        "comment_id must be unique within the batch",
    ]


def test_validate_comment_dataset_does_not_mutate_input_records():
    invalid_comment = VALID_COMMENT.copy()
    invalid_comment["comment_id"] = None

    validate_comment_dataset([invalid_comment])

    assert "validation_errors" not in invalid_comment
