from datetime import datetime, timedelta, timezone

from transformation.comment_deduplicator import (
    select_latest_comment_versions,
)


BASE_COMMENT = {
    "comment_id": "comment-1",
    "comment_text": "Original text",
    "updated_at": datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc),
    "ingested_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
}


def test_select_latest_comment_versions_prefers_later_update():
    older_comment = BASE_COMMENT.copy()
    newer_comment = BASE_COMMENT.copy()
    newer_comment["comment_text"] = "Edited text"
    newer_comment["updated_at"] = datetime(
        2026,
        8,
        19,
        9,
        0,
        tzinfo=timezone.utc,
    )

    selected_comments = select_latest_comment_versions(
        [newer_comment, older_comment]
    )

    assert selected_comments == [newer_comment]


def test_select_latest_comment_versions_uses_ingestion_time_as_tiebreaker():
    earlier_ingestion = BASE_COMMENT.copy()
    later_ingestion = BASE_COMMENT.copy()
    later_ingestion["like_count"] = 2
    later_ingestion["ingested_at"] = datetime(
        2026,
        8,
        20,
        9,
        0,
        tzinfo=timezone.utc,
    )

    selected_comments = select_latest_comment_versions(
        [earlier_ingestion, later_ingestion]
    )

    assert selected_comments == [later_ingestion]


def test_select_latest_comment_versions_normalizes_timezone_comparison():
    utc_comment = BASE_COMMENT.copy()
    offset_comment = BASE_COMMENT.copy()
    offset_comment["comment_text"] = "Later absolute update"
    offset_comment["updated_at"] = datetime(
        2026,
        8,
        19,
        17,
        0,
        tzinfo=timezone(timedelta(hours=8)),
    )

    selected_comments = select_latest_comment_versions(
        [utc_comment, offset_comment]
    )

    assert selected_comments == [offset_comment]


def test_select_latest_comment_versions_keeps_first_exact_tie_and_id_order():
    first_version = BASE_COMMENT.copy()
    tied_version = BASE_COMMENT.copy()
    tied_version["comment_text"] = "Conflicting tied text"
    other_comment = BASE_COMMENT.copy()
    other_comment["comment_id"] = "comment-2"

    selected_comments = select_latest_comment_versions(
        [first_version, other_comment, tied_version]
    )

    assert selected_comments == [first_version, other_comment]
