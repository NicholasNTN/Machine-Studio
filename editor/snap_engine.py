from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapResult:
    value: float
    target: float | None = None
    snapped: bool = False
    target_kind: str = ""


class SnapEngine:
    def __init__(self, threshold_seconds: float = 0.08):
        self.threshold_seconds = max(0.0, float(threshold_seconds))

    def snap(self, value: float, targets, threshold: float | None = None) -> SnapResult:
        source = float(value)
        limit = self.threshold_seconds if threshold is None else max(0.0, float(threshold))
        candidates = []
        for target in targets:
            if isinstance(target, tuple):
                position, kind = target
            else:
                position, kind = target, "edge"
            position = float(position)
            candidates.append((abs(position - source), position, str(kind)))
        if not candidates:
            return SnapResult(source)
        distance, position, kind = min(candidates, key=lambda item: item[0])
        if distance <= limit:
            return SnapResult(position, position, True, kind)
        return SnapResult(source)
