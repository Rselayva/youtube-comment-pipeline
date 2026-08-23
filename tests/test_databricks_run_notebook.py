from pathlib import Path


NOTEBOOK_PATH = Path("databricks/run_pipeline_notebook.py")


def test_databricks_run_notebook_is_parameterized_and_compilable():
    source = NOTEBOOK_PATH.read_text(encoding="utf-8")

    compile(source, str(NOTEBOOK_PATH), "exec")
    assert source.startswith("# Databricks notebook source")
    assert 'dbutils.secrets.get(' in source
    assert 'os.environ["YOUTUBE_API_KEY"]' in source
    assert "PipelineStorage.under(pipeline_root)" in source
    assert "load_gold_manifest_to_databricks" in source
    assert "rselayva_dev" not in source
    assert "your_api_key" not in source.lower()
