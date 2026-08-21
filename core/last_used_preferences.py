from __future__ import annotations

from copy import deepcopy
import math


def safe_int(value, fallback=0):
    try:
        number = float(value)
        return int(number) if math.isfinite(number) else int(fallback)
    except (TypeError, ValueError, OverflowError):
        return int(fallback)


def safe_float(value, fallback=0.0):
    try:
        number = float(value)
        return number if math.isfinite(number) else float(fallback)
    except (TypeError, ValueError, OverflowError):
        return float(fallback)


def safe_bool(value, fallback=False):
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try: return bool(value) if math.isfinite(float(value)) else bool(fallback)
        except (TypeError, ValueError, OverflowError): return bool(fallback)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}: return True
        if normalized in {"0", "false", "no", "off", ""}: return False
    return bool(fallback)


def safe_str(value, fallback=""):
    if value is None or isinstance(value, (dict, list, tuple, set)): return str(fallback)
    try: return str(value)
    except Exception: return str(fallback)


def safe_splitter_sizes(value):
    if not isinstance(value, dict): return {}
    result = {}
    for key in ("workspace_horizontal", "workspace_vertical"):
        raw = value.get(key)
        if isinstance(raw, (list, tuple)) and raw:
            result[key] = [max(0, safe_int(item, 0)) for item in raw]
    return result


class LastUsedPreferences:
    """Application defaults only; never stores timeline content or media paths."""
    CONTENT_KEYS = {"clips", "editor_clips", "editor_layers", "subtitle", "subtitle_editor_text", "narration_path", "blur_zones", "preview_cues"}

    def __init__(self, settings_data):
        self.settings_data = settings_data if isinstance(settings_data, dict) else {}
        raw = self.settings_data.get("last_used_preferences", {})
        self.values = deepcopy(raw) if isinstance(raw, dict) else {}

    def update(self, **values):
        for key, value in values.items():
            if key not in self.CONTENT_KEYS: self.values[key] = deepcopy(value)
        self.settings_data["last_used_preferences"] = deepcopy(self.values)

    def text_defaults(self):
        return {key[5:]: value for key, value in self.values.items() if key.startswith("text_")}
