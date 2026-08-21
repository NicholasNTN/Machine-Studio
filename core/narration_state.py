from __future__ import annotations

from copy import deepcopy
from os import PathLike


def _path(value) -> str:
    return str(value).strip() if isinstance(value, (str, PathLike)) else ""


def begin_narration_generation(state: dict) -> dict:
    """Mark the active sequence's synchronized derivative stale before TTS work."""
    result = deepcopy(state or {})
    try:
        revision = max(0, int(result.get("narration_revision", 0))) + 1
    except (TypeError, ValueError):
        revision = 1
    result["narration_revision"] = revision
    result["narration_synced_revision"] = max(0, revision - 1)
    return result


def finish_narration_generation(state: dict, synced_path: str) -> dict:
    """Publish the newly built sequence-local synchronized narration atomically."""
    result = deepcopy(state or {})
    try:
        revision = max(1, int(result.get("narration_revision", 1)))
    except (TypeError, ValueError):
        revision = 1
    path = _path(synced_path)
    result.update({
        "narration_path": path,
        "narration_source_path": path,
        "narration_synced_path": path,
        "narration_revision": revision,
        "narration_synced_revision": revision,
    })
    return result


def resolve_export_narration(state: dict, preview_path="") -> str:
    """Resolve only one sequence; its active preview source is current truth."""
    preview = _path(preview_path)
    if preview:
        return preview
    values = dict(state or {})
    source = _path(values.get("narration_source_path"))
    synced = _path(values.get("narration_synced_path"))
    try:
        revision = int(values.get("narration_revision", 0))
        synced_revision = int(values.get("narration_synced_revision", 0))
    except (TypeError, ValueError):
        revision = synced_revision = 0
    if synced and synced_revision >= revision:
        return synced
    if source:
        return source
    return _path(values.get("narration_path"))
