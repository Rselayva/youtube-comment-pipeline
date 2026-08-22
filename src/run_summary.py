import argparse
import json
from datetime import timezone
from pathlib import Path

from storage.run_manifest_reader import (
    read_latest_run_manifest,
    read_latest_successful_run_manifest,
    read_run_manifest_history,
)
from storage.run_manifest_writer import DEFAULT_RUN_MANIFESTS_DIR
from video_input import extract_video_id


def build_run_summary(manifest: dict) -> dict:
    summary = {
        "run_id": manifest["run_id"],
        "status": manifest["status"],
        "video_id": manifest["video_id"],
        "started_at": manifest["started_at"].astimezone(
            timezone.utc
        ).isoformat(),
        "completed_at": manifest["completed_at"].astimezone(
            timezone.utc
        ).isoformat(),
        "execution_time_seconds": manifest["execution_time_seconds"],
        "parameters": manifest["parameters"],
        "dictionary_versions": manifest["dictionary_versions"],
        "counts": manifest["counts"],
        "artifacts": manifest["artifacts"],
    }
    if manifest["status"] == "failed":
        summary["failure"] = manifest["failure"]

    return summary


def get_latest_run_summary(
    video_id: str,
    base_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> dict | None:
    manifest = read_latest_run_manifest(video_id, base_dir)
    if manifest is None:
        return None
    return build_run_summary(manifest)


def get_latest_successful_run_summary(
    video_id: str,
    base_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> dict | None:
    manifest = read_latest_successful_run_manifest(video_id, base_dir)
    if manifest is None:
        return None
    return build_run_summary(manifest)


def get_run_history_summaries(
    video_id: str,
    limit: int,
    base_dir: Path = DEFAULT_RUN_MANIFESTS_DIR,
) -> list[dict]:
    manifests = read_run_manifest_history(video_id, limit, base_dir)
    return [build_run_summary(manifest) for manifest in manifests]


def parse_history_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "history limit must be an integer from 1 to 100"
        ) from error
    if not 1 <= limit <= 100:
        raise argparse.ArgumentTypeError(
            "history limit must be an integer from 1 to 100"
        )
    return limit


def parse_summary_cli_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show pipeline run summaries for one YouTube video.",
    )
    parser.add_argument(
        "video",
        metavar="VIDEO",
        help="YouTube video ID or URL",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--latest-successful",
        action="store_true",
        help="show the latest successful run",
    )
    selection.add_argument(
        "--history",
        type=parse_history_limit,
        metavar="N",
        help="show the latest N runs, from 1 to 100",
    )
    args = parser.parse_args(argv)

    try:
        args.video = extract_video_id(args.video)
    except ValueError as error:
        parser.error(str(error))
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_summary_cli_args(argv)

    if args.latest_successful:
        summary = get_latest_successful_run_summary(args.video)
        if summary is None:
            raise SystemExit(
                f"No successful run manifests found for video: {args.video}"
            )
    elif args.history is not None:
        summary = get_run_history_summaries(args.video, args.history)
        if not summary:
            raise SystemExit(
                f"No run manifests found for video: {args.video}"
            )
    else:
        summary = get_latest_run_summary(args.video)
        if summary is None:
            raise SystemExit(
                f"No run manifests found for video: {args.video}"
            )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
