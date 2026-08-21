from __future__ import annotations


STYLE_IDS = {
    "Before and after": "BEFORE_AND_AFTER",
    "Mystery and curiosity": "MYSTERY_AND_CURIOSITY",
}

DUAL_VOICE_ROLES = {
    "BEFORE_AND_AFTER": (("before", "Before Voice"), ("after", "After Voice")),
    "MYSTERY_AND_CURIOSITY": (("setup", "Setup / Mystery"), ("reveal", "Reveal / Explanation")),
}


def style_id(display_name: str) -> str:
    return STYLE_IDS.get(str(display_name), str(display_name).upper().replace(" ", "_"))


def dual_voice_roles(display_name: str):
    return DUAL_VOICE_ROLES.get(style_id(display_name))


def assign_role(display_name: str, index: int, total: int, supplied: str = "") -> str:
    roles = dual_voice_roles(display_name)
    if not roles: return "single"
    valid = {roles[0][0], roles[1][0]}
    if supplied in valid: return supplied
    return roles[0][0] if int(index) < max(1, int(total) // 2) else roles[1][0]


def voice_for_role(role: str, voice_a: str, voice_b: str, display_name: str) -> str:
    roles = dual_voice_roles(display_name)
    return voice_b if roles and role == roles[1][0] else voice_a
