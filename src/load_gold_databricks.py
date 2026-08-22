from pathlib import Path
from typing import Any

from warehouse.databricks_adapter import (
    DatabricksGoldAdapter,
    DatabricksGoldConfig,
)
from warehouse.gold_load_service import load_latest_successful_gold


def load_gold_to_databricks(
    video_id: str,
    spark: Any,
    catalog: str,
    schema: str,
    manifests_dir: Path,
) -> dict:
    config = DatabricksGoldConfig(catalog=catalog, schema=schema)
    adapter = DatabricksGoldAdapter(spark=spark, config=config)
    return load_latest_successful_gold(
        video_id=video_id,
        adapter=adapter,
        manifests_dir=manifests_dir,
    )
