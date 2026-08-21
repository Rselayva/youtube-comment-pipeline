from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import run_summary


VIDEO_ID = "aFrQIJ5cbRc"


def make_manifest(status: str = "succeeded") -> dict:
    manifest = {
        "schema_version": 1,
        "run_id": f"{VIDEO_ID}_20260821T090000000000Z",
        "status": status,
        "video_id": VIDEO_ID,
        "started_at": datetime(
            2026, 8, 21, 9, 0, tzinfo=timezone.utc
        ),
        "completed_at": datetime(
            2026, 8, 21, 9, 0, 2, tzinfo=timezone.utc
        ),
        "execution_time_seconds": 2.0,
        "parameters": {"max_pages": 2, "page_size": 10},
        "dictionary_versions": {"entity": "nmixx_v2"},
        "counts": {"records_parsed": 10},
        "artifacts": {"silver_comments": "silver.jsonl"},
    }
    if status == "failed":
        manifest["failure"] = {
            "stage": "transformation",
            "error_type": "ValueError",
        }
    return manifest


def test_build_run_summary_includes_failure_only_for_failed_runs():
    success_summary = run_summary.build_run_summary(make_manifest())
    failed_summary = run_summary.build_run_summary(
        make_manifest("failed")
    )

    assert "failure" not in success_summary
    assert failed_summary["failure"] == {
        "stage": "transformation",
        "error_type": "ValueError",
    }
    assert success_summary["started_at"] == "2026-08-21T09:00:00+00:00"


@patch("run_summary.get_latest_run_summary")
def test_run_summary_cli_accepts_youtube_url_and_prints_json(
    mock_get_latest_run_summary,
    capsys,
):
    mock_get_latest_run_summary.return_value = {
        "video_id": VIDEO_ID,
        "status": "succeeded",
    }

    run_summary.main(
        [f"https://www.youtube.com/watch?v={VIDEO_ID}"]
    )

    mock_get_latest_run_summary.assert_called_once_with(VIDEO_ID)
    output = capsys.readouterr().out
    assert f'"video_id": "{VIDEO_ID}"' in output
    assert '"status": "succeeded"' in output


@patch("run_summary.get_latest_run_summary", return_value=None)
def test_run_summary_cli_exits_when_no_manifest_exists(
    mock_get_latest_run_summary,
):
    with pytest.raises(
        SystemExit,
        match=f"No run manifests found for video: {VIDEO_ID}",
    ):
        run_summary.main([VIDEO_ID])

    mock_get_latest_run_summary.assert_called_once_with(VIDEO_ID)
