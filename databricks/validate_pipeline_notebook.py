# Databricks notebook source
# MAGIC %md
# MAGIC # YouTube Comment Pipeline — Publication Reconciliation
# MAGIC
# MAGIC Confirms that the latest publication audit counts match both immutable
# MAGIC Delta history and the four current views for one video.

# COMMAND ----------
import json
import sys
from pathlib import Path


dbutils.widgets.text("catalog", "", "Unity Catalog catalog")
dbutils.widgets.text("schema", "", "Target schema")
dbutils.widgets.text("video_id", "", "YouTube video ID")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
video_id = dbutils.widgets.get("video_id").strip()


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src").is_dir():
            return candidate
    raise RuntimeError("Could not locate repository src directory")


repo_root = find_repo_root(Path.cwd())
sys.path.insert(0, str(repo_root / "src"))

from warehouse.databricks_validation import (
    validate_latest_gold_publication,
)

# COMMAND ----------
result = validate_latest_gold_publication(
    video_id=video_id,
    spark=spark,
    catalog=catalog,
    schema=schema,
)
print(json.dumps(result, indent=2))
