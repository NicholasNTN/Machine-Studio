from __future__ import annotations


def cache_processed_preview_result(sequences, origin_sequence_id: str, active_sequence_id: str, path: str) -> bool:
    """Cache for the origin sequence and report whether it is still safe to display."""
    origin = next((sequence for sequence in sequences if sequence.id == origin_sequence_id), None)
    if origin is None:
        return False
    origin.ai_project["processed_preview_path"] = str(path or "")
    return origin_sequence_id == active_sequence_id
