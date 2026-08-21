import argparse
import json
from datetime import timezone
from pathlib import Path

from storage.run_manifest_reader import read_latest_run_manifest
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


def parse_summary_cli_args(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(
        description="Show the latest pipeline run for one YouTube video.",
    )
    parser.add_argument(
        "video",
        metavar="VIDEO",
        help="YouTube video ID or URL",
    )
    args = parser.parse_args(argv)

    try:
        return extract_video_id(args.video)
    except ValueError as error:
        parser.error(str(error))


def main(argv: list[str] | None = None) -> None:
    video_id = parse_summary_cli_args(argv)
    summary = get_latest_run_summary(video_id)
    if summary is None:
        raise SystemExit(f"No run manifests found for video: {video_id}")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
