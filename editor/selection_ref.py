from dataclasses import dataclass


@dataclass(frozen=True)
class SelectionRef:
    kind: str
    object_id: str
    group_id: str = ""
