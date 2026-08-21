import json
from datetime import date, datetime, timedelta, timezone

import pytest

from storage.topic_metrics_writer import (
    write_daily_topic_metrics_snapshot,
    write_video_topic_metrics_snapshot,
)


def make_metric() -> dict:
    return {
        "video_id": "video-1",
        "topic_id": "vocal",
        "display_name": "Vocal",
        "dictionary_version": "comment_topics_v1",
        "comment_count": 3,
        "topic_comment_count": 2,
        "comment_share_of_voice": 2 / 3,
        "topic_comment_count_total": 3,
        "topic_share_of_voice": 2 / 3,
        "snapshot_at": datetime(
            2026,
            8,
            21,
            20,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
    }


def test_write_video_topic_metrics_snapshot_writes_versioned_jsonl(
    tmp_path,
):
    output_path = write_video_topic_metrics_snapshot(
        [make_metric()],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )

    assert output_path == (
        tmp_path
        / "comment_topics_v1"
        / "video-1"
        / "current_metrics.jsonl"
    )
    saved_metric = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_metric["topic_id"] == "vocal"
    assert saved_metric["snapshot_at"] == "2026-08-21T12:00:00+00:00"


def test_write_daily_topic_metrics_snapshot_serializes_date(tmp_path):
    metric = {**make_metric(), "comment_date": date(2026, 8, 21)}

    output_path = write_daily_topic_metrics_snapshot(
        [metric],
        "video-1",
        "comment_topics_v1",
        tmp_path,
    )

    saved_metric = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_metric["comment_date"] == "2026-08-21"


def test_write_topic_metrics_snapshot_replaces_previous_content(tmp_path):
    first_metric = make_metric()
    output_path = write_video_topic_metrics_snapshot(
        [first_metric], "video-1", "comment_topics_v1", tmp_path
    )
    second_metric = {**first_metric, "topic_id": "dance"}

    replaced_path = write_video_topic_metrics_snapshot(
        [second_metric], "video-1", "comment_topics_v1", tmp_path
    )

    assert replaced_path == output_path
    saved_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(saved_lines) == 1
    assert json.loads(saved_lines[0])["topic_id"] == "dance"


def test_write_topic_metrics_snapshot_removes_partial_file_on_failure(
    tmp_path,
):
    invalid_metric = make_metric()
    del invalid_metric["snapshot_at"]

    with pytest.raises(KeyError, match="snapshot_at"):
        write_video_topic_metrics_snapshot(
            [invalid_metric],
            "video-1",
            "comment_topics_v1",
            tmp_path,
        )

    output_dir = tmp_path / "comment_topics_v1" / "video-1"
    assert list(output_dir.iterdir()) == []
