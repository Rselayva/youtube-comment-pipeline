from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from warehouse.gold_load_service import (
    load_gold_from_manifest_file,
    load_latest_successful_gold,
)


VIDEO_ID = "aFrQIJ5cbRc"


@patch("warehouse.gold_load_service.load_gold_manifest")
@patch(
    "warehouse.gold_load_service.read_latest_successful_run_manifest"
)
def test_load_latest_successful_gold_delegates_to_adapter(
    mock_read_latest_successful_run_manifest,
    mock_load_gold_manifest,
    tmp_path,
):
    manifest = {
        "run_id": f"{VIDEO_ID}_20260821T120000000000Z",
        "video_id": VIDEO_ID,
    }
    adapter = Mock()
    manifests_dir = tmp_path / "manifests"
    mock_read_latest_successful_run_manifest.return_value = manifest
    mock_load_gold_manifest.return_value = {
        "gold_video_entity_sov": 7,
    }

    result = load_latest_successful_gold(
        VIDEO_ID,
        adapter,
        manifests_dir,
    )

    mock_read_latest_successful_run_manifest.assert_called_once_with(
        VIDEO_ID,
        manifests_dir,
    )
    mock_load_gold_manifest.assert_called_once_with(manifest, adapter)
    assert result == {
        "run_id": manifest["run_id"],
        "video_id": VIDEO_ID,
        "loaded_rows": {"gold_video_entity_sov": 7},
    }


@patch(
    "warehouse.gold_load_service.read_latest_successful_run_manifest",
    return_value=None,
)
def test_load_latest_successful_gold_rejects_missing_successful_run(
    mock_read_latest_successful_run_manifest,
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match=f"No successful run manifests found for video: {VIDEO_ID}",
    ):
        load_latest_successful_gold(
            VIDEO_ID,
            Mock(),
            tmp_path / "manifests",
        )


@patch("warehouse.gold_load_service.load_gold_manifest")
@patch("warehouse.gold_load_service.read_run_manifest")
def test_load_gold_from_manifest_file_loads_exact_run(
    mock_read_run_manifest,
    mock_load_gold_manifest,
):
    manifest_path = Path("/Volumes/catalog/schema/volume/run.json")
    manifest = {"run_id": "run-123", "video_id": VIDEO_ID}
    adapter = Mock()
    mock_read_run_manifest.return_value = manifest
    mock_load_gold_manifest.return_value = {"table": 4}

    result = load_gold_from_manifest_file(manifest_path, adapter)

    mock_read_run_manifest.assert_called_once_with(manifest_path)
    mock_load_gold_manifest.assert_called_once_with(manifest, adapter)
    assert result == {
        "run_id": "run-123",
        "video_id": VIDEO_ID,
        "loaded_rows": {"table": 4},
    }
