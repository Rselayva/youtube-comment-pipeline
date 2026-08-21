import json
from datetime import date, datetime, timedelta, timezone

import pytest

from storage.entity_sov_writer import (
    write_daily_entity_sov_snapshot,
    write_video_entity_sov_snapshot,
)


def make_metric() -> dict:
    return {
        "video_id": "video-1",
        "entity_type": "member",
        "entity_id": "nmixx_haewon",
        "group_id": "nmixx",
        "canonical_name": "HAEWON",
        "dictionary_version": "nmixx_v2",
        "comment_count": 3,
        "mention_comment_count": 2,
        "comment_share_of_voice": 2 / 3,
        "entity_type_mention_comment_count": 2,
        "entity_share_of_voice": 1.0,
        "snapshot_at": datetime(
            2026,
            8,
            21,
            20,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
    }


def test_write_video_entity_sov_snapshot_writes_versioned_jsonl(tmp_path):
    metric = make_metric()

    output_path = write_video_entity_sov_snapshot(
        [metric],
        "video-1",
        "nmixx_v2",
        tmp_path,
    )

    assert output_path == (
        tmp_path / "nmixx_v2" / "video-1" / "current_metrics.jsonl"
    )
    saved_metric = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_metric["entity_id"] == "nmixx_haewon"
    assert saved_metric["snapshot_at"] == "2026-08-21T12:00:00+00:00"


def test_write_daily_entity_sov_snapshot_serializes_comment_date(tmp_path):
    metric = {**make_metric(), "comment_date": date(2026, 8, 21)}

    output_path = write_daily_entity_sov_snapshot(
        [metric],
        "video-1",
        "nmixx_v2",
        tmp_path,
    )

    saved_metric = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved_metric["comment_date"] == "2026-08-21"


def test_entity_sov_snapshot_replaces_previous_content(tmp_path):
    first_metric = make_metric()
    output_path = write_video_entity_sov_snapshot(
        [first_metric], "video-1", "nmixx_v2", tmp_path
    )
    second_metric = {**first_metric, "entity_id": "nmixx_lily"}

    replaced_path = write_video_entity_sov_snapshot(
        [second_metric], "video-1", "nmixx_v2", tmp_path
    )

    assert replaced_path == output_path
    saved_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(saved_lines) == 1
    assert json.loads(saved_lines[0])["entity_id"] == "nmixx_lily"


def test_entity_sov_snapshot_rejects_invalid_metrics_before_writing(
    tmp_path,
):
    invalid_metric = make_metric()
    invalid_metric["entity_share_of_voice"] = 0.5

    with pytest.raises(
        ValueError,
        match="entity_share_of_voice does not match",
    ):
        write_video_entity_sov_snapshot(
            [invalid_metric], "video-1", "nmixx_v2", tmp_path
        )

    assert not (tmp_path / "nmixx_v2" / "video-1").exists()
