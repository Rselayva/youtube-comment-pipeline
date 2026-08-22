from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from storage.run_manifest_writer import validate_run_manifest


GOLD_TABLE_ARTIFACTS = {
    "gold_video_entity_sov": "gold_video_entity_sov",
    "gold_daily_entity_sov": "gold_daily_entity_sov",
    "gold_video_topic_metrics": "gold_video_topic_metrics",
    "gold_daily_topic_metrics": "gold_daily_topic_metrics",
}

TABLE_DICTIONARY_TYPES = {
    "gold_video_entity_sov": "entity",
    "gold_daily_entity_sov": "entity",
    "gold_video_topic_metrics": "topic",
    "gold_daily_topic_metrics": "topic",
}


@dataclass(frozen=True)
class GoldSnapshotLoad:
    table_name: str
    source_uri: str
    video_id: str
    dictionary_version: str


class GoldWarehouseAdapter(Protocol):
    def load_snapshots(
        self,
        snapshots: tuple[GoldSnapshotLoad, ...],
    ) -> dict[str, int]: ...


def prepare_gold_snapshot_loads(
    manifest: dict,
) -> tuple[GoldSnapshotLoad, ...]:
    validate_run_manifest(manifest)
    if manifest["status"] != "succeeded":
        raise ValueError("Only succeeded run manifests can be loaded")

    dictionary_versions = manifest["dictionary_versions"]
    if set(dictionary_versions) != {"entity", "topic"}:
        raise ValueError(
            "dictionary_versions must contain entity and topic"
        )
    for dictionary_type, version in dictionary_versions.items():
        if not isinstance(version, str) or not version.strip():
            raise ValueError(
                f"dictionary_versions.{dictionary_type} must be non-empty"
            )

    snapshots = []
    for table_name, artifact_name in GOLD_TABLE_ARTIFACTS.items():
        raw_path = manifest["artifacts"].get(artifact_name)
        if not isinstance(raw_path, (str, Path)):
            raise ValueError(
                f"Missing Gold artifact location: {artifact_name}"
            )
        source_uri = str(raw_path)
        if not source_uri.strip():
            raise ValueError(
                f"Missing Gold artifact location: {artifact_name}"
            )
        dictionary_type = TABLE_DICTIONARY_TYPES[table_name]
        snapshots.append(
            GoldSnapshotLoad(
                table_name=table_name,
                source_uri=source_uri,
                video_id=manifest["video_id"],
                dictionary_version=dictionary_versions[dictionary_type],
            )
        )

    return tuple(snapshots)


def load_gold_manifest(
    manifest: dict,
    adapter: GoldWarehouseAdapter,
) -> dict[str, int]:
    snapshots = prepare_gold_snapshot_loads(manifest)
    return adapter.load_snapshots(snapshots)
