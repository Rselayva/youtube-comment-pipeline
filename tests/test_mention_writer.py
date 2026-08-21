import json
from datetime import datetime, timedelta, timezone

import pytest

from storage.mention_writer import write_mention_snapshot


def make_mention() -> dict:
    return {
        "comment_id": "comment-1",
        "video_id": "video-1",
        "entity_type": "member",
        "entity_id": "nmixx_haewon",
        "group_id": "nmixx",
        "canonical_name": "HAEWON",
        "matched_aliases": ("海嫄", "吳海嫄"),
        "mention_count": 1,
        "published_at": datetime(
            2026,
            8,
            21,
            17,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ),
        "ingested_at": datetime(
            2026,
            8,
            21,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        "dictionary_version": "nmixx_v2",
    }


def test_write_mention_snapshot_writes_versioned_current_snapshot(tmp_path):
    mention = make_mention()

    output_path = write_mention_snapshot(
        mentions=[mention],
        video_id="video-1",
        dictionary_version="nmixx_v2",
        base_dir=tmp_path,
    )

    assert output_path == (
        tmp_path / "nmixx_v2" / "video-1" / "current_mentions.jsonl"
    )
    saved_mentions = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]
    assert saved_mentions == [
        {
            **mention,
            "matched_aliases": ["海嫄", "吳海嫄"],
            "published_at": "2026-08-21T09:00:00+00:00",
            "ingested_at": "2026-08-21T10:00:00+00:00",
        }
    ]


def test_write_mention_snapshot_replaces_previous_snapshot(tmp_path):
    first_mention = make_mention()
    output_path = write_mention_snapshot(
        [first_mention],
        "video-1",
        "nmixx_v2",
        tmp_path,
    )

    second_mention = {
        **first_mention,
        "comment_id": "comment-2",
        "entity_id": "nmixx_lily",
        "canonical_name": "LILY",
        "matched_aliases": ("莉莉",),
    }
    replaced_path = write_mention_snapshot(
        [second_mention],
        "video-1",
        "nmixx_v2",
        tmp_path,
    )

    assert replaced_path == output_path
    saved_lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(saved_lines) == 1
    assert json.loads(saved_lines[0])["comment_id"] == "comment-2"


def test_write_mention_snapshot_can_clear_previous_snapshot(tmp_path):
    output_path = write_mention_snapshot(
        [make_mention()],
        "video-1",
        "nmixx_v2",
        tmp_path,
    )

    write_mention_snapshot([], "video-1", "nmixx_v2", tmp_path)

    assert output_path.read_text(encoding="utf-8") == ""


def test_write_mention_snapshot_does_not_mutate_input(tmp_path):
    mention = make_mention()

    write_mention_snapshot(
        [mention],
        "video-1",
        "nmixx_v2",
        tmp_path,
    )

    assert mention["matched_aliases"] == ("海嫄", "吳海嫄")
    assert isinstance(mention["published_at"], datetime)


def test_write_mention_snapshot_removes_partial_file_on_failure(tmp_path):
    invalid_mention = make_mention()
    del invalid_mention["ingested_at"]

    with pytest.raises(KeyError, match="ingested_at"):
        write_mention_snapshot(
            [invalid_mention],
            "video-1",
            "nmixx_v2",
            tmp_path,
        )

    output_dir = tmp_path / "nmixx_v2" / "video-1"
    assert list(output_dir.iterdir()) == []
