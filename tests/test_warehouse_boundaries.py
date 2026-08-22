import ast
from pathlib import Path


SRC_DIR = Path("src")
DUCKDB_ADAPTER_PATH = Path("src/warehouse/duckdb_adapter.py")


def imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(
                alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_only_duckdb_adapter_imports_duckdb_in_production_code():
    duckdb_importers = {
        path
        for path in SRC_DIR.rglob("*.py")
        if "duckdb" in imported_top_level_modules(path)
    }

    assert duckdb_importers == {DUCKDB_ADAPTER_PATH}


def test_duckdb_dependency_is_optional_and_isolated():
    shared_requirements = Path("requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    duckdb_requirements = Path("requirements-duckdb.txt").read_text(
        encoding="utf-8"
    ).splitlines()

    assert "duckdb" not in shared_requirements
    assert duckdb_requirements == ["-r requirements.txt", "duckdb"]


def test_databricks_adapter_uses_runtime_injected_spark_only():
    imported_modules = imported_top_level_modules(
        Path("src/warehouse/databricks_adapter.py")
    )

    assert "pyspark" not in imported_modules
    assert "databricks" not in imported_modules
