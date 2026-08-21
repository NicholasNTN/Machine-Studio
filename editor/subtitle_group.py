from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class SubtitleGroupStyle:
    font_name: str = "Arial"
    font_size: int = 48
    bold: bool = True
    italic: bool = False
    color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: float = 3.0
    shadow: float = 1.0
    alignment: str = "center"
    x_percent: float = 50.0
    y_percent: float = 86.0
    background_box: bool = False
    background_color: str = "#000000"
    background_opacity: int = 65
    animation: str = "Không"

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**{key: value for key, value in dict(data or {}).items() if key in cls.__dataclass_fields__})


@dataclass
class SubtitleGroup:
    id: str
    source_type: str
    source_path: str
    style: SubtitleGroupStyle = field(default_factory=SubtitleGroupStyle)
    segment_ids: list[str] = field(default_factory=list)
    visible: bool = True

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, data):
        values = dict(data or {}); values["style"] = SubtitleGroupStyle.from_dict(values.get("style", {})); return cls(**values)


def subtitle_group_is_visible(enabled: bool, group: SubtitleGroup | None) -> bool:
    """Professional group visibility is authoritative; legacy track state is irrelevant."""
    return bool(enabled and group is not None and group.visible)


def active_subtitle_render_state(enabled: bool, group: SubtitleGroup | None, cues, playhead: float):
    """Selection-free subtitle state for the active sequence preview."""
    if not subtitle_group_is_visible(enabled, group):
        return False, "", float(playhead), float(playhead)
    second = float(playhead or 0.0)
    for cue in cues or []:
        start, end, text = cue[:3]
        if float(start) <= second < float(end):
            return True, str(text), float(start), float(end)
    return True, "", second, second
