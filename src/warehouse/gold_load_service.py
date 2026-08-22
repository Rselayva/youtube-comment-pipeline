from pathlib import Path

from storage.run_manifest_reader import (
    read_latest_successful_run_manifest,
)
from storage.run_manifest_writer import DEFAULT_RUN_MANIFESTS_DIR
from warehouse.gold_load_contract import (
    GoldWarehouseAdapter,
    load_gold_manifest,
)


def load_latest_successful_gold(
    video_id: str,
    adapter: GoldWarehouseAdapter,
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

    return {
        "run_id": manifest["run_id"],
        "video_id": video_id,
        "loaded_rows": load_gold_manifest(manifest, adapter),
    }
