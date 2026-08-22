from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import shutil
from pathlib import Path
from uuid import uuid4

from core.models import AIProject
from editor.sequence_manager import SequenceManager


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_project_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return (slug[:48].rstrip("-") or "untitled-project")


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    project_path: str
    managed: bool
    created_at: str
    updated_at: str
    last_opened_at: str = ""
    thumbnail_source: str = ""
    media_count: int = 0
    duration: float = 0.0
    missing: bool = False


class ProjectManager:
    MAX_RECENT = 50

    def __init__(self, root: str | Path, settings=None):
        self.root = Path(root).resolve()
        self.projects_root = self.root / "projects"
        self.settings = settings

    @property
    def _settings_data(self) -> dict:
        if self.settings is None:
            return {}
        return self.settings.data if hasattr(self.settings, "data") else self.settings

    def _save_settings(self):
        if self.settings is not None and hasattr(self.settings, "save"):
            self.settings.save()

    @staticmethod
    def canonical_path(path: str | Path) -> str:
        return str(Path(path).expanduser().resolve())

    def is_managed(self, path: str | Path) -> bool:
        project_path = Path(path).resolve()
        try:
            relative = project_path.relative_to(self.projects_root.resolve())
        except ValueError:
            return False
        return len(relative.parts) == 2 and relative.parts[0] != ".trash" and relative.name == "project.json"

    def _record(self, path: str | Path) -> ProjectRecord:
        project_path = Path(path).resolve()
        project = AIProject.load(project_path)
        cached_thumbnail = project_path.parent / "thumbnail.jpg"
        thumbnail = str(cached_thumbnail) if cached_thumbnail.is_file() else next((item for item in project.media_library if Path(item).is_file()), "")
        if not thumbnail and project.video_path and Path(project.video_path).is_file():
            thumbnail = project.video_path
        opened = self._settings_data.get("project_last_opened", {}).get(str(project_path), "")
        return ProjectRecord(
            project_id=project.project_id,
            name=project.name,
            project_path=str(project_path),
            managed=self.is_managed(project_path),
            created_at=project.created_at,
            updated_at=project.updated_at,
            last_opened_at=opened,
            thumbnail_source=thumbnail,
            media_count=len(project.media_library),
            duration=float(project.duration or 0.0),
        )

    def _unique_name(self, requested: str) -> str:
        base = str(requested or "Untitled Project").strip() or "Untitled Project"
        names = {record.name.casefold() for record in self.discover_projects()}
        if base.casefold() not in names:
            return base
        index = 2
        while f"{base} {index}".casefold() in names:
            index += 1
        return f"{base} {index}"

    def create_project(self, name="Untitled Project") -> ProjectRecord:
        display_name = self._unique_name(name)
        project_id = str(uuid4())
        folder = self.projects_root / f"{safe_project_slug(display_name)}_{project_id.split('-')[0]}"
        folder.mkdir(parents=True, exist_ok=False)
        now = utc_now()
        manager = SequenceManager()
        packed = manager.to_dict()
        project = AIProject(
            project_id=project_id,
            name=display_name,
            created_at=now,
            updated_at=now,
            workspace=str(folder),
            active_sequence_id=packed["active_sequence_id"],
            sequences=packed["sequences"],
        )
        path = folder / "project.json"
        project.save(path)
        self.register_project(path)
        return self._record(path)

    def discover_projects(self, sort="modified") -> list[ProjectRecord]:
        candidates = []
        if self.projects_root.is_dir():
            candidates.extend(self.projects_root.glob("*/project.json"))
        data = self._settings_data
        candidates.extend(data.get("recent_project_paths", []) if isinstance(data.get("recent_project_paths", []), list) else [])
        if data.get("last_project"):
            candidates.append(data["last_project"])
        records = []
        seen = set()
        valid_recent = []
        for candidate in candidates:
            try:
                canonical = self.canonical_path(candidate)
            except (OSError, ValueError):
                continue
            folded = canonical.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            if not Path(canonical).is_file():
                continue
            try:
                records.append(self._record(canonical)); valid_recent.append(canonical)
            except (OSError, ValueError, TypeError):
                continue
        if isinstance(data.get("recent_project_paths"), list):
            recent_set = {item.casefold() for item in valid_recent}
            cleaned = [self.canonical_path(item) for item in data["recent_project_paths"] if Path(item).is_file() and self.canonical_path(item).casefold() in recent_set]
            if cleaned != data["recent_project_paths"]:
                data["recent_project_paths"] = cleaned[:self.MAX_RECENT]; self._save_settings()
        if sort == "name_asc": records.sort(key=lambda item: item.name.casefold())
        elif sort == "name_desc": records.sort(key=lambda item: item.name.casefold(), reverse=True)
        elif sort == "created": records.sort(key=lambda item: item.created_at, reverse=True)
        else: records.sort(key=lambda item: item.updated_at, reverse=True)
        return records

    def register_project(self, path: str | Path):
        canonical = self.canonical_path(path)
        recent = self._settings_data.setdefault("recent_project_paths", [])
        recent[:] = [item for item in recent if self.canonical_path(item).casefold() != canonical.casefold()]
        recent.insert(0, canonical); del recent[self.MAX_RECENT:]
        self._save_settings()

    def touch_project(self, path: str | Path):
        canonical = self.canonical_path(path); now = utc_now()
        opened = self._settings_data.setdefault("project_last_opened", {}); opened[canonical] = now
        self._settings_data["last_project"] = canonical
        self.register_project(canonical)

    def open_project(self, path: str | Path) -> AIProject:
        project = AIProject.load(path); self.touch_project(path); return project

    def rename_project(self, path: str | Path, name: str) -> ProjectRecord:
        display_name = str(name or "").strip()
        if not display_name:
            raise ValueError("Project name cannot be empty")
        project_path = Path(path).resolve(); project = AIProject.load(project_path)
        project.name = display_name; project.updated_at = utc_now(); project.save(project_path)
        self.register_project(project_path)
        return self._record(project_path)

    def remove_recent_project(self, path: str | Path):
        canonical = self.canonical_path(path)
        recent = self._settings_data.setdefault("recent_project_paths", [])
        recent[:] = [item for item in recent if self.canonical_path(item).casefold() != canonical.casefold()]
        opened = self._settings_data.get("project_last_opened", {}); opened.pop(canonical, None)
        if str(self._settings_data.get("last_project", "")).casefold() == canonical.casefold():
            self._settings_data["last_project"] = ""
        self._save_settings()

    def delete_project(self, path: str | Path) -> Path | None:
        project_path = Path(path).resolve()
        if not self.is_managed(project_path):
            self.remove_recent_project(project_path); return None
        folder = project_path.parent
        is_junction = bool(getattr(folder, "is_junction", lambda: False)())
        if folder.is_symlink() or is_junction or not project_path.is_file():
            raise ValueError("Managed project path is not safe to move")
        trash = self.projects_root / ".trash"; trash.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = trash / f"{stamp}_{folder.name}"
        suffix = 2
        while destination.exists():
            destination = trash / f"{stamp}_{folder.name}_{suffix}"; suffix += 1
        shutil.move(str(folder), str(destination))
        self.remove_recent_project(project_path)
        return destination
