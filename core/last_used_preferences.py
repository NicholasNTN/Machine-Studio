from __future__ import annotations

from copy import deepcopy


class LastUsedPreferences:
    """Application defaults only; never stores timeline content or media paths."""
    CONTENT_KEYS = {"clips", "editor_clips", "editor_layers", "subtitle", "subtitle_editor_text", "narration_path", "blur_zones", "preview_cues"}

    def __init__(self, settings_data):
        self.settings_data = settings_data
        self.values = deepcopy(settings_data.get("last_used_preferences", {}) or {})

    def update(self, **values):
        for key, value in values.items():
            if key not in self.CONTENT_KEYS: self.values[key] = deepcopy(value)
        self.settings_data["last_used_preferences"] = deepcopy(self.values)

    def text_defaults(self):
        return {key[5:]: value for key, value in self.values.items() if key.startswith("text_")}
