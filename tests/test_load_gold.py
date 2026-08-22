import json
from pathlib import Path
from unittest.mock import patch

import pytest

import load_gold


VIDEO_ID = "aFrQIJ5cbRc"


@patch("load_gold.load_gold_snapshots")
@patch("load_gold.read_latest_successful_run_manifest")
def test_load_latest_successful_gold_uses_manifest_artifacts(
    mock_read_latest_successful_run_manifest,
    mock_load_gold_snapshots,
    tmp_path,
):
    manifest = {
        "run_id": f"{VIDEO_ID}_20260821T120000000000Z",
        "video_id": VIDEO_ID,
    }
    mock_read_latest_successful_run_manifest.return_value = manifest
    mock_load_gold_snapshots.return_value = {
        "gold_video_entity_sov": 7,
    }
    database_path = tmp_path / "warehouse.duckdb"
    manifests_dir = tmp_path / "manifests"

    result = load_gold.load_latest_successful_gold(
        VIDEO_ID,
        database_path,
        manifests_dir,
    )

    mock_read_latest_successful_run_manifest.assert_called_once_with(
        VIDEO_ID,
        manifests_dir,
    )
    mock_load_gold_snapshots.assert_called_once_with(
        manifest,
        database_path,
    )
    assert result == {
        "run_id": manifest["run_id"],
        "video_id": VIDEO_ID,
        "database_path": str(database_path),
        "loaded_rows": {"gold_video_entity_sov": 7},
    }


@patch("load_gold.read_latest_successful_run_manifest", return_value=None)
def test_load_latest_successful_gold_rejects_missing_successful_run(
    mock_read_latest_successful_run_manifest,
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match=f"No successful run manifests found for video: {VIDEO_ID}",
    ):
        load_gold.load_latest_successful_gold(
            VIDEO_ID,
            tmp_path / "warehouse.duckdb",
            tmp_path / "manifests",
        )


@patch("load_gold.load_latest_successful_gold")
def test_load_gold_cli_accepts_url_database_and_prints_json(
    mock_load_latest_successful_gold,
    capsys,
):
    database_path = Path("custom.duckdb")
    mock_load_latest_successful_gold.return_value = {
        "video_id": VIDEO_ID,
        "database_path": str(database_path),
    }

    load_gold.main(
        [
            f"https://www.youtube.com/watch?v={VIDEO_ID}",
            "--database",
            str(database_path),
        ]
    )

    mock_load_latest_successful_gold.assert_called_once_with(
        video_id=VIDEO_ID,
        database_path=database_path,
    )
    assert json.loads(capsys.readouterr().out)["video_id"] == VIDEO_ID
