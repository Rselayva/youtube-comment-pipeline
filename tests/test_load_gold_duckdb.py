import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytest.importorskip("duckdb")

import load_gold_duckdb


VIDEO_ID = "aFrQIJ5cbRc"


@patch("load_gold_duckdb.load_latest_successful_gold")
@patch("load_gold_duckdb.DuckDBGoldAdapter")
def test_load_gold_duckdb_cli_uses_adapter_and_prints_json(
    mock_adapter_class,
    mock_load_latest_successful_gold,
    capsys,
):
    database_path = Path("custom.duckdb")
    adapter = Mock()
    mock_adapter_class.return_value = adapter
    mock_load_latest_successful_gold.return_value = {
        "run_id": f"{VIDEO_ID}_20260821T120000000000Z",
        "video_id": VIDEO_ID,
        "loaded_rows": {"gold_video_entity_sov": 7},
    }

    load_gold_duckdb.main(
        [
            f"https://www.youtube.com/watch?v={VIDEO_ID}",
            "--database",
            str(database_path),
        ]
    )

    mock_adapter_class.assert_called_once_with(
        database_path=database_path
    )
    mock_load_latest_successful_gold.assert_called_once_with(
        VIDEO_ID,
        adapter,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["database_path"] == str(database_path)
