from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core import ffmpeg_engine as ffm
from .background_jobs import BackgroundJobs


class ThumbnailService(QObject):
    """Background ffprobe/frame extraction with mtime-aware disk caching."""
    ready = Signal(str, str, float)
    failed = Signal(str)

    def __init__(self, cache_dir: str | Path, parent=None):
        super().__init__(parent); self.cache_dir = Path(cache_dir); self.jobs = BackgroundJobs(); self._pending = set(); self._cache = {}

    def request(self, source: str) -> None:
        path = Path(source)
        if not path.exists() or source in self._pending: return
        stamp = f"{path.resolve()}|{path.stat().st_mtime_ns}"
        key = hashlib.sha1(stamp.encode("utf-8", errors="ignore")).hexdigest()
        target = self.cache_dir / f"{key}.jpg"
        cached = self._cache.get(source)
        if cached and Path(cached[0]).exists(): self.ready.emit(source, cached[0], cached[1]); return
        self._pending.add(source)
        def work():
            info = ffm.probe(source); duration = float(info.get("duration", 0.0) or 0.0)
            thumb = ffm.extract_preview_still(source, str(target), at_seconds=min(2.0, max(0.1, duration * 0.08)), width=360)
            return thumb, duration
        job = self.jobs.submit(work)
        def done(result):
            self._pending.discard(source); self._cache[source] = result; self.ready.emit(source, result[0], result[1])
        job.signals.finished.connect(done)
        job.signals.failed.connect(lambda _tb: (self._pending.discard(source), self.failed.emit(source)))
