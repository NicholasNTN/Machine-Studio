from __future__ import annotations


def active_editor_source(clips):
    active = [clip for clip in (clips or []) if clip.get("enabled", True) and str(clip.get("path", "")).strip()]
    if not active:
        return "empty", ""
    if len(active) == 1:
        return "single", str(active[0]["path"])
    return "proxy", ""


def find_origin_sequence(sequences, sequence_id):
    return next((sequence for sequence in sequences if sequence.id == sequence_id), None)
