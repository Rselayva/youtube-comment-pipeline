from pathlib import Path
from unittest.mock import Mock, patch

from load_gold_databricks import load_gold_to_databricks


VIDEO_ID = "aFrQIJ5cbRc"


@patch("load_gold_databricks.load_latest_successful_gold")
@patch("load_gold_databricks.DatabricksGoldAdapter")
@patch("load_gold_databricks.DatabricksGoldConfig")
def test_load_gold_to_databricks_uses_external_runtime_configuration(
    mock_config_class,
    mock_adapter_class,
    mock_load_latest_successful_gold,
):
    spark = Mock()
    config = Mock()
    adapter = Mock()
    manifests_dir = Path("/Volumes/audience/prod/manifests")
    mock_config_class.return_value = config
    mock_adapter_class.return_value = adapter
    mock_load_latest_successful_gold.return_value = {
        "video_id": VIDEO_ID,
    }

    result = load_gold_to_databricks(
        video_id=VIDEO_ID,
        spark=spark,
        catalog="audience",
        schema="gold",
        manifests_dir=manifests_dir,
    )

    mock_config_class.assert_called_once_with(
        catalog="audience",
        schema="gold",
    )
    mock_adapter_class.assert_called_once_with(
        spark=spark,
        config=config,
    )
    mock_load_latest_successful_gold.assert_called_once_with(
        video_id=VIDEO_ID,
        adapter=adapter,
        manifests_dir=manifests_dir,
    )
    assert result == {"video_id": VIDEO_ID}
