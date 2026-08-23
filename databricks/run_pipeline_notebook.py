# Databricks notebook source
# MAGIC %md
# MAGIC # YouTube Comment Pipeline — End-to-End Run
# MAGIC
# MAGIC Reads the API credential from a Databricks Secret, writes all artifacts
# MAGIC to a Unity Catalog Volume, and publishes the exact run to Delta tables.

# COMMAND ----------
import json
import os
import re
import sys
from pathlib import Path


dbutils.widgets.text("video_id", "", "YouTube video ID")
dbutils.widgets.text("max_pages", "2", "Maximum comment pages")
dbutils.widgets.text("page_size", "100", "Comments per page")
dbutils.widgets.text("catalog", "", "Unity Catalog catalog")
dbutils.widgets.text("schema", "", "Target schema")
dbutils.widgets.text("volume", "", "Pipeline data Volume")
dbutils.widgets.text(
    "secret_scope",
    "youtube-comment-pipeline",
    "Databricks Secret scope",
)
dbutils.widgets.text(
    "secret_key",
    "youtube-api-key",
    "YouTube API Secret key",
)

parameters = {
    name: dbutils.widgets.get(name).strip()
    for name in (
        "video_id",
        "max_pages",
        "page_size",
        "catalog",
        "schema",
        "volume",
        "secret_scope",
        "secret_key",
    )
}

identifier_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
for field_name in ("catalog", "schema", "volume"):
    if not identifier_pattern.fullmatch(parameters[field_name]):
        raise ValueError(
            f"{field_name} must contain only letters, numbers, and underscores"
        )
for field_name in ("video_id", "secret_scope", "secret_key"):
    if not parameters[field_name]:
        raise ValueError(f"{field_name} must not be empty")


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src").is_dir():
            return candidate
    raise RuntimeError("Could not locate repository src directory")


repo_root = find_repo_root(Path.cwd())
sys.path.insert(0, str(repo_root / "src"))

from storage.pipeline_storage import PipelineStorage
from video_input import extract_video_id, parse_max_pages, parse_page_size


video_id = extract_video_id(parameters["video_id"])
max_pages = parse_max_pages(parameters["max_pages"])
page_size = parse_page_size(parameters["page_size"])
pipeline_root = Path(
    f"/Volumes/{parameters['catalog']}/{parameters['schema']}/"
    f"{parameters['volume']}/youtube_comment_pipeline"
)
storage = PipelineStorage.under(pipeline_root)

# Read the secret before importing main; the YouTube client reads the
# environment variable while its module is initialized.
os.environ["YOUTUBE_API_KEY"] = dbutils.secrets.get(
    scope=parameters["secret_scope"],
    key=parameters["secret_key"],
)

from load_gold_databricks import load_gold_manifest_to_databricks
from main import configure_logging, main

# COMMAND ----------
configure_logging()
manifest_path = main(
    video_id=video_id,
    max_pages=max_pages,
    page_size=page_size,
    storage=storage,
)
load_result = load_gold_manifest_to_databricks(
    manifest_path=manifest_path,
    spark=spark,
    catalog=parameters["catalog"],
    schema=parameters["schema"],
)

result = {
    "status": "succeeded",
    "catalog": parameters["catalog"],
    "schema": parameters["schema"],
    "volume": parameters["volume"],
    "video_id": video_id,
    "manifest_path": str(manifest_path),
    **load_result,
}
print(json.dumps(result, indent=2))
