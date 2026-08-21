from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from uuid import uuid4
import re


@dataclass
class SequenceDocument:
    id: str
    name: str
    state: dict = field(default_factory=dict)
    ai_project: dict = field(default_factory=dict)
    playhead: float = 0.0
    dirty: bool = False
    undo_history: list = field(default_factory=list, repr=False)
    name_mode: str = "auto"

    def to_dict(self):
        value = asdict(self); value.pop("undo_history", None); return value

    @classmethod
    def from_dict(cls, value):
        data = dict(value or {})
        name = str(data.get("name") or "Timeline")
        inferred_mode = "auto" if re.fullmatch(r"Timeline(?: \d+)?", name) else "custom"
        return cls(str(data.get("id") or uuid4().hex), str(data.get("name") or "Timeline"),
                   deepcopy(data.get("state") or {}), deepcopy(data.get("ai_project") or {}),
                   float(data.get("playhead", 0) or 0), bool(data.get("dirty", False)),
                   name_mode=str(data.get("name_mode") or inferred_mode))


class SequenceManager:
    """Owns independent editing documents; UI/runtime bind only to active."""

    def __init__(self, sequences=None, active_sequence_id=""):
        self.sequences = list(sequences or [SequenceDocument(uuid4().hex, "Timeline")])
        self.active_sequence_id = active_sequence_id if any(s.id == active_sequence_id for s in self.sequences) else self.sequences[0].id
        self.renumber_auto_names()

    @property
    def active(self): return next(s for s in self.sequences if s.id == self.active_sequence_id)

    def create(self, name=""):
        sequence = SequenceDocument(uuid4().hex, name or "Timeline", name_mode="custom" if str(name).strip() else "auto")
        self.sequences.append(sequence); self.active_sequence_id = sequence.id; self.renumber_auto_names(); return sequence

    def renumber_auto_names(self):
        auto_index = 0
        for sequence in self.sequences:
            if sequence.name_mode != "auto":
                continue
            sequence.name = "Timeline" if auto_index == 0 else f"Timeline {auto_index}"
            auto_index += 1

    def activate(self, sequence_id):
        if any(s.id == sequence_id for s in self.sequences): self.active_sequence_id = sequence_id; return self.active
        raise KeyError(sequence_id)

    def duplicate(self, sequence_id):
        source = next(s for s in self.sequences if s.id == sequence_id)
        copy = SequenceDocument(uuid4().hex, f"{source.name} Copy", deepcopy(source.state), deepcopy(source.ai_project), source.playhead, True, name_mode="custom")
        self.sequences.append(copy); self.active_sequence_id = copy.id; return copy

    def rename(self, sequence_id, name):
        sequence = next(s for s in self.sequences if s.id == sequence_id)
        if str(name).strip(): sequence.name = str(name).strip(); sequence.name_mode = "custom"
        return sequence

    def close(self, sequence_id):
        self.sequences[:] = [s for s in self.sequences if s.id != sequence_id]
        if not self.sequences: self.sequences.append(SequenceDocument(uuid4().hex, "Timeline"))
        if not any(s.id == self.active_sequence_id for s in self.sequences): self.active_sequence_id = self.sequences[0].id
        self.renumber_auto_names()
        return self.active

    def to_dict(self): return {"active_sequence_id": self.active_sequence_id, "sequences": [s.to_dict() for s in self.sequences]}

    @classmethod
    def from_dict(cls, value, legacy_state=None, legacy_project=None):
        data = dict(value or {})
        if data.get("sequences"):
            return cls([SequenceDocument.from_dict(s) for s in data["sequences"]], str(data.get("active_sequence_id", "")))
        first = SequenceDocument(uuid4().hex, "Timeline", deepcopy(legacy_state or {}), deepcopy(legacy_project or {}))
        return cls([first], first.id)
