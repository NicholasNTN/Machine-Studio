from __future__ import annotations

import os
from pathlib import Path


def canonical_media_key(path) -> str:
    try:
        return os.path.normcase(os.path.abspath(str(Path(str(path)))))
    except (TypeError, ValueError, OSError):
        return str(path or "").strip().casefold()


def migrate_global_media_library(media_library, display_names, sequences):
    """Union root and legacy per-sequence media without modifying clip references."""
    result = []
    names = dict(display_names or {}) if isinstance(display_names, dict) else {}
    seen = set()

    def add(path):
        text = str(path or "").strip()
        key = canonical_media_key(text)
        if text and key not in seen:
            seen.add(key); result.append(text)

    for path in media_library or []:
        add(path)
    for sequence in sequences or []:
        state = sequence.state if hasattr(sequence, "state") else dict(sequence or {}).get("state", {})
        if not isinstance(state, dict):
            continue
        for path in state.get("media_bin", []) or []:
            add(path)
        legacy_names = state.get("media_display_names", {})
        if isinstance(legacy_names, dict):
            for path, name in legacy_names.items():
                names.setdefault(str(path), str(name))
    return result, names
