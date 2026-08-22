import argparse
import json
from pathlib import Path

from video_input import extract_video_id
from warehouse.duckdb_adapter import (
    DEFAULT_DUCKDB_PATH,
    DuckDBGoldAdapter,
)
from warehouse.gold_load_service import load_latest_successful_gold


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
    adapter = DuckDBGoldAdapter(database_path=args.database)
    try:
        result = load_latest_successful_gold(args.video, adapter)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    result["database_path"] = str(args.database)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
