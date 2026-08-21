from __future__ import annotations

import json

from .ai_styles import AIStyleMetadata, get_style


def semantic_fallback(segments: list[dict], style_value: str) -> list[dict]:
    """Conservative section-aware fallback used only when AI metadata is absent."""
    style = get_style(style_value)
    if style.voice_mode == "single":
        return [{**segment, "speaker_role": style.speaker_roles[0], "confidence": 1.0} for segment in segments]
    first, second = style.speaker_roles[:2]
    result, switched = [], False
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "")).strip().lower()
        supplied = str(segment.get("speaker_role", ""))
        if segment.get("role_locked") and supplied in style.speaker_roles:
            role, confidence = supplied, 1.0
        elif supplied in style.speaker_roles:
            role, confidence = supplied, float(segment.get("confidence", 0.95))
        elif style.id == "mystery_curiosity":
            role, confidence = (first, 0.72) if index == 0 else (second, 0.68)
        elif style.id == "before_after":
            if any(marker in text for marker in ("after", "now", "result", "finally", "transformed")): switched = True
            role, confidence = (second if switched else first), 0.62
        elif style.id == "problem_solution":
            if any(marker in text for marker in ("solution", "solve", "answer", "fix", "instead")): switched = True
            role, confidence = (second if switched else first), 0.62
        elif style.id in {"question_answer", "interview"}:
            role, confidence = (first if not switched else second), 0.55
            switched = not switched
        else:
            role, confidence = (first if index == 0 else second), 0.50
        result.append({**segment, "speaker_role": role, "confidence": confidence})
    return result


def build_classifier_prompt(segments: list[dict], style_value: str) -> str:
    style = get_style(style_value)
    compact = [{"id": item.get("id", str(index)), "text": item.get("text", "")} for index, item in enumerate(segments)]
    return f"""Classify speaker roles semantically for a video script.
Style: {style.id} — {style.description}
Allowed roles: {json.dumps(style.speaker_roles)}
Keep coherent sections on one speaker. Do not alternate by sentence, paragraph, or punctuation. A rhetorical question may remain with an explainer.
Return ONLY JSON array: [{{"id":"...","speaker_role":"...","confidence":0.0}}]
Segments: {json.dumps(compact, ensure_ascii=False)}"""


def analyze_speaker_roles(segments: list[dict], style_value: str, ai_classifier=None) -> list[dict]:
    style: AIStyleMetadata = get_style(style_value)
    if style.voice_mode == "single": return semantic_fallback(segments, style.id)
    locked = {str(item.get("id")): item for item in segments if item.get("role_locked")}
    if ai_classifier is not None:
        try:
            classified = ai_classifier(build_classifier_prompt(segments, style.id))
            by_id = {str(item.get("id")): item for item in classified if item.get("speaker_role") in style.speaker_roles}
            output = []
            for index, segment in enumerate(segments):
                segment_id = str(segment.get("id", index))
                if segment_id in locked: output.append(dict(segment)); continue
                item = by_id.get(segment_id, {})
                output.append({**segment, "speaker_role": item.get("speaker_role", ""), "confidence": float(item.get("confidence", 0.0) or 0.0)})
            return semantic_fallback(output, style.id)
        except Exception:
            pass
    return semantic_fallback(segments, style.id)
