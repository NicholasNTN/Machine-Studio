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


def sequence_narration_path(sequences, sequence_id):
    """Resolve narration solely from the stable sequence id; never another UI mirror."""
    sequence = find_origin_sequence(sequences, sequence_id)
    if sequence is None or not isinstance(sequence.state, dict): return ""
    value = sequence.state.get("narration_path", "")
    return str(value).strip() if not isinstance(value, (dict, list, tuple)) else ""
