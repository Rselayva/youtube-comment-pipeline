import argparse
import json
from pathlib import Path

from storage.duckdb_gold_loader import (
    DEFAULT_DUCKDB_PATH,
    load_gold_snapshots,
)
from storage.run_manifest_reader import (
    read_latest_successful_run_manifest,
)
from storage.run_manifest_writer import DEFAULT_RUN_MANIFESTS_DIR
from video_input import extract_video_id


def load_latest_successful_gold(
    video_id: str,
    database_path: Path = DEFAULT_DUCKDB_PATH,
    manifests_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> dict:
    manifest = read_latest_successful_run_manifest(
        video_id,
        manifests_dir,
    )
    if manifest is None:
        raise ValueError(
            f"No successful run manifests found for video: {video_id}"
        )

    loaded_rows = load_gold_snapshots(manifest, database_path)
    return {
        "run_id": manifest["run_id"],
        "video_id": video_id,
        "database_path": str(database_path),
        "loaded_rows": loaded_rows,
    }


def parse_load_cli_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load the latest successful Gold snapshots into DuckDB."
        ),
    )
    parser.add_argument(
        "video",
        metavar="VIDEO",
        help="YouTube video ID or URL",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DUCKDB_PATH,
        metavar="PATH",
        help=f"DuckDB file path (default: {DEFAULT_DUCKDB_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        args.video = extract_video_id(args.video)
    except ValueError as error:
        parser.error(str(error))
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_load_cli_args(argv)
    try:
        result = load_latest_successful_gold(
            video_id=args.video,
            database_path=args.database,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
