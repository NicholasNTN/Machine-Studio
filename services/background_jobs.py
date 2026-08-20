from __future__ import annotations

import traceback
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class JobSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class BackgroundJob(QRunnable):
    def __init__(self, function: Callable, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = JobSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(self.function(*self.args, **self.kwargs))
        except Exception:
            self.signals.failed.emit(traceback.format_exc())


class BackgroundJobs:
    def __init__(self, pool: QThreadPool | None = None):
        self.pool = pool or QThreadPool.globalInstance()

    def submit(self, function: Callable, *args, **kwargs) -> BackgroundJob:
        job = BackgroundJob(function, *args, **kwargs)
        self.pool.start(job)
        return job
