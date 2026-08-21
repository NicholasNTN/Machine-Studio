from __future__ import annotations

from pathlib import Path


class FileDialogHistory:
    """Local navigation history backed by settings, never project content."""
    def __init__(self, settings_data, save=None):
        self.settings_data = settings_data if isinstance(settings_data, dict) else {}
        raw = self.settings_data.get("file_dialog_history", {})
        self.values = dict(raw) if isinstance(raw, dict) else {}
        self._save = save

    def initial_path(self, key, fallback=""):
        candidates = [self.values.get(key), fallback]
        for candidate in candidates:
            if not candidate: continue
            path = Path(str(candidate)).expanduser()
            if path.is_file(): path = path.parent
            while not path.exists() and path != path.parent: path = path.parent
            if path.exists(): return str(path)
        return str(Path.home())

    def remember_file(self, key, path):
        value = Path(str(path)).expanduser()
        self.remember_dir(key, value.parent)

    def remember_dir(self, key, path):
        if not path: return
        self.values[str(key)] = str(Path(str(path)).expanduser())
        self.settings_data["file_dialog_history"] = dict(self.values)
        if self._save: self._save()

    def remember_save(self, key, path): self.remember_file(key, path)
