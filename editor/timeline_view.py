from __future__ import annotations

from dataclasses import dataclass
import math


NICE_TICK_INTERVALS = (0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300)


@dataclass(frozen=True)
class TimelineView:
    visible_duration: float
    pixels_per_second: float
    major_tick_interval: float


def compute_auto_timeline_view(viewport_width, content_duration, *, header_width=132.0,
                               target_density=12.0, target_tick_pixels=60.0) -> TimelineView:
    """Fit a readable time range to the viewport without changing media duration."""
    usable_width = max(1.0, float(viewport_width) - max(0.0, float(header_width)))
    content = max(0.0, float(content_duration or 0.0))
    breathing_room = max(5.0, content * 0.05)
    density_span = usable_width / max(1.0, float(target_density))
    visible_duration = max(5.0, density_span, content + breathing_room)
    pixels_per_second = usable_width / visible_duration
    desired_tick = max(0.1, float(target_tick_pixels)) / max(0.01, pixels_per_second)
    major_tick = min(NICE_TICK_INTERVALS, key=lambda value: abs(math.log(value / desired_tick)))
    return TimelineView(visible_duration, pixels_per_second, major_tick)
