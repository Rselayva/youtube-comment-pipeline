from pathlib import Path


NOTEBOOK_PATH = Path("databricks/validate_pipeline_notebook.py")


def test_validation_notebook_is_parameterized_and_compilable():
    source = NOTEBOOK_PATH.read_text(encoding="utf-8")

    compile(source, str(NOTEBOOK_PATH), "exec")
    assert source.startswith("# Databricks notebook source")
    assert "validate_latest_gold_publication" in source
    assert "rselayva_dev" not in source
    assert "YOUTUBE_API_KEY" not in source
