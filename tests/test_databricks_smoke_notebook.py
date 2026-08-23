from pathlib import Path


NOTEBOOK_PATH = Path("databricks/smoke_test_notebook.py")
GUIDE_PATH = Path("docs/DATABRICKS_SMOKE_TEST.md")


def test_databricks_smoke_notebook_is_safe_and_compilable():
    source = NOTEBOOK_PATH.read_text(encoding="utf-8")

    compile(source, str(NOTEBOOK_PATH), "exec")
    assert source.startswith("# Databricks notebook source")
    assert "schema name must contain smoke or test" in source
    assert "YOUTUBE_API_KEY" not in source
    assert "requests" not in source
    assert 'video_id = "smokeTst001"' in source


def test_databricks_smoke_guide_references_the_notebook():
    guide = GUIDE_PATH.read_text(encoding="utf-8")

    assert "databricks/smoke_test_notebook.py" in guide
    assert "youtube_comment_pipeline_smoke" in guide
