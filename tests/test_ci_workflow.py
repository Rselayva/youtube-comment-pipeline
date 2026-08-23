from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/ci.yml")


def test_ci_workflow_runs_full_duckdb_test_environment():
    source = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "actions/checkout@v6" in source
    assert "actions/setup-python@v6" in source
    assert 'python-version: "3.12"' in source
    assert "requirements-duckdb.txt" in source
    assert "python -m pytest -q" in source
    assert "contents: read" in source
    assert "YOUTUBE_API_KEY" not in source
