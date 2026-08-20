from __future__ import annotations

from pathlib import Path
import base64
import json
import re
import wave
from typing import Callable, Optional

from .models import Scene


class GeminiError(RuntimeError):
    pass


def _client(api_key: str):
    key = (api_key or "").strip()
    if not key:
        raise GeminiError("Chưa nhập Gemini API key.")
    try:
        from google import genai
        from google.genai import types

        # Do not let a transient API/socket issue leave the desktop app
        # waiting for tens of minutes. 90 seconds is enough for the fast path.
        return genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=90000),
        )
    except Exception as e:
        raise GeminiError(f"Không khởi tạo được Google GenAI SDK: {e}") from e


def _friendly(e: Exception) -> GeminiError:
    s = str(e)
    low = s.lower()
    if "401" in low or "authentication" in low or "credential" in low:
        return GeminiError(
            "Gemini báo 401 Authentication. Hãy tạo/kiểm tra API key trong Google AI Studio, "
            "dán lại ở Settings và bấm Test Gemini."
        )
    if "429" in low or "quota" in low or "resource_exhausted" in low:
        return GeminiError("Gemini báo 429: hết quota hoặc rate limit.")
    if "404" in low or "not_found" in low:
        return GeminiError("Không tìm thấy model/API endpoint. Kiểm tra model trong Settings.")
    return GeminiError(s)


def _call(fn):
    try:
        return fn()
    except GeminiError:
        raise
    except Exception as e:
        raise _friendly(e) from e


def _json_array(text: str):
    text = (text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            for k in ("scenes", "items", "results"):
                if isinstance(obj.get(k), list):
                    return obj[k]
    except Exception:
        pass
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        raise GeminiError("AI không trả JSON array hợp lệ.")
    return json.loads(m.group(0))


def test(api_key: str, model: str) -> str:
    c = _client(api_key)
    r = _call(lambda: c.interactions.create(
        model=model,
        input="Reply with exactly OK",
        store=False,
    ))
    return (r.output_text or "").strip()



def _json_object(text: str):
    text = (text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Strip common markdown fences and locate the broadest JSON object.
    clean = text.replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(clean)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(clean[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    raise GeminiError("AI không trả JSON hợp lệ cho chế độ nhanh.")


def _fast_generation_config(model: str) -> dict:
    m = (model or "").lower()
    # Gemini 3.7 Flash supports low thinking. Flash-Lite / 3.5 / 3.6
    # support minimal thinking, which is useful for low-latency extraction.
    if "3.7-flash" in m:
        return {"thinking_level": "low"}
    if "flash-lite" in m or "3.6-flash" in m or "3.5-flash" in m:
        return {"thinking_level": "minimal"}
    return {}


def fast_analyze_and_script(
    api_key: str,
    model: str,
    scenes: list[Scene],
    market: str = "US",
    style: str = "Factory documentary",
    audio_path: str = "",
):
    """ONE model call: understand frames (+ optional audio) and write script.

    This replaces the old 2A -> 2B -> 2C -> 3 sequence for the default path.
    """
    if not scenes:
        raise GeminiError("Không có frame để AI phân tích.")

    c = _client(api_key)

    prompt = f"""You are the single-pass video analyst and script writer for Machine Studio.

TARGET MARKET: {market}
STYLE: {style}

You are given a small set of representative frames sampled from a machine,
factory, invention, or production-process video. There may also be source audio.

Do ALL tasks in one pass:
1. Understand what the video is mainly showing.
2. Identify visible machines/materials/processes only when reasonably confident.
3. Read useful visible Chinese text when legible; never invent unreadable text.
4. Use source audio only if supplied and useful.
5. Write ORIGINAL narration for every supplied time segment.
6. English should sound natural for a US audience, not like a literal translation.
7. Scene 0 should be a strong curiosity hook.
8. Keep narration short enough for the scene (roughly 2.0-2.3 English words/sec).
9. Never fabricate exact specifications, prices, speeds, capacities, temperatures,
   dates, or names unless clearly supported by visible/audio evidence.
10. Also provide a Vietnamese translation so the editor can verify the meaning.

Return ONLY one JSON object exactly in this shape:
{{
  "topic": "short topic",
  "summary": "2-5 concise sentences explaining the whole video and any uncertainty",
  "transcript": "only useful source-audio meaning, or empty string",
  "scenes": [
    {{
      "index": 0,
      "visual": "what is visibly happening",
      "chinese_text": "legible Chinese text or empty string",
      "source_meaning": "concise meaning of visible/source information",
      "en_voice": "original US English narration",
      "vi_voice": "Vietnamese translation"
    }}
  ]
}}

IMPORTANT: Return one scene item for EVERY supplied frame index.
"""

    inputs = [{"type": "text", "text": prompt}]
    for s in scenes:
        inputs.append({
            "type": "text",
            "text": (
                f"FRAME index={s.index}; time={s.start:.2f}-{s.end:.2f}s; "
                f"duration={s.duration:.2f}s"
            )
        })
        data = base64.b64encode(Path(s.frame_path).read_bytes()).decode("ascii")
        inputs.append({
            "type": "image",
            "data": data,
            "mime_type": "image/jpeg",
        })

    # Audio is OPTIONAL and OFF by default in the UI because upload + audio
    # understanding adds latency. When enabled it is still part of this one model call.
    if audio_path and Path(audio_path).exists():
        uploaded = _call(lambda: c.files.upload(file=audio_path))
        inputs.append({"type": "text", "text": "OPTIONAL SOURCE AUDIO:"})
        inputs.append({
            "type": "audio",
            "uri": uploaded.uri,
            "mime_type": uploaded.mime_type,
        })

    cfg = _fast_generation_config(model)
    kwargs = dict(model=model, input=inputs, store=False)
    if cfg:
        kwargs["generation_config"] = cfg

    r = _call(lambda: c.interactions.create(**kwargs))
    obj = _json_object(r.output_text)

    by_index = {}
    for item in obj.get("scenes", []) or []:
        try:
            by_index[int(item.get("index"))] = item
        except Exception:
            continue

    for s in scenes:
        item = by_index.get(s.index, {})
        s.visual = str(item.get("visual", "") or "").strip()
        s.chinese_text = str(item.get("chinese_text", "") or "").strip()
        s.source_meaning = str(item.get("source_meaning", "") or "").strip()
        s.en_voice = str(item.get("en_voice", "") or "").strip()
        s.vi_voice = str(item.get("vi_voice", "") or "").strip()

    return {
        "topic": str(obj.get("topic", "") or "").strip(),
        "summary": str(obj.get("summary", "") or "").strip(),
        "transcript": str(obj.get("transcript", "") or "").strip(),
        "scenes": scenes,
    }

def analyze_frames(
    api_key: str,
    model: str,
    scenes: list[Scene],
    progress: Optional[Callable[[int, int], None]] = None,
    batch_size: int = 8,
):
    c = _client(api_key)
    total = len(scenes)

    for pos in range(0, total, batch_size):
        batch = scenes[pos:pos + batch_size]
        prompt = """You analyze frames from a factory, machine, invention, or production-process video.

For each supplied frame:
- Describe the visible action.
- Identify machine/material/product only when reasonably confident.
- Read visible Chinese text when legible.
- Explain the likely meaning in concise English.
- Never invent specifications or unreadable words.

Return ONLY JSON array:
[
 {"index":0,"visual":"...","chinese_text":"...","source_meaning":"..."}
]
"""
        inp = [{"type": "text", "text": prompt}]
        for s in batch:
            inp.append({
                "type": "text",
                "text": f"FRAME index={s.index}, time={s.start:.1f}-{s.end:.1f}s"
            })
            data = base64.b64encode(Path(s.frame_path).read_bytes()).decode("ascii")
            inp.append({"type": "image", "data": data, "mime_type": "image/jpeg"})

        r = _call(lambda: c.interactions.create(
            model=model, input=inp, store=False
        ))
        arr = _json_array(r.output_text)
        by = {}
        for item in arr:
            try:
                by[int(item.get("index"))] = item
            except Exception:
                pass
        for s in batch:
            item = by.get(s.index, {})
            s.visual = str(item.get("visual", "")).strip()
            s.chinese_text = str(item.get("chinese_text", "")).strip()
            s.source_meaning = str(item.get("source_meaning", "")).strip()
        if progress:
            progress(min(pos + len(batch), total), total)
    return scenes


def transcribe_audio(api_key: str, model: str, audio_path: str) -> str:
    if not audio_path or not Path(audio_path).exists():
        return ""
    c = _client(api_key)
    uploaded = _call(lambda: c.files.upload(file=audio_path))
    prompt = """Understand the source audio of this video.
If there is speech, return a concise timestamped transcript/meaning.
If Chinese, include English meaning. Preserve useful factual information.
If there is no useful speech, return NO_USEFUL_SPEECH.
Do not invent inaudible words."""
    r = _call(lambda: c.interactions.create(
        model=model,
        input=[
            {"type": "text", "text": prompt},
            {"type": "audio", "uri": uploaded.uri, "mime_type": uploaded.mime_type},
        ],
        store=False,
    ))
    return (r.output_text or "").strip()


def global_understanding(
    api_key: str,
    model: str,
    scenes: list[Scene],
    transcript: str,
) -> str:
    c = _client(api_key)
    compact = [
        {
            "time": f"{s.start:.1f}-{s.end:.1f}",
            "visual": s.visual,
            "text": s.chinese_text,
            "meaning": s.source_meaning,
        }
        for s in scenes
    ]
    prompt = f"""Act as a video content analyst.
Using the scene evidence and source-audio context below, explain:
1. What the video is mainly about.
2. What machine/process/product is shown.
3. Step-by-step flow of what happens.
4. Important facts that are supported by the evidence.
5. Uncertain points the script writer must NOT claim as fact.
6. A one-line topic label.

SCENES:
{json.dumps(compact, ensure_ascii=False)}

SOURCE AUDIO:
{(transcript or "No useful source audio.")[:18000]}
"""
    r = _call(lambda: c.interactions.create(
        model=model, input=prompt, store=False
    ))
    return (r.output_text or "").strip()


def generate_script(
    api_key: str,
    model: str,
    scenes: list[Scene],
    transcript: str,
    understanding: str,
    market: str = "US",
    style: str = "Factory documentary",
    progress: Optional[Callable[[int, int], None]] = None,
    batch_size: int = 18,
):
    c = _client(api_key)
    total = len(scenes)
    source = (transcript or "")[:12000]
    summary = (understanding or "")[:12000]

    for pos in range(0, total, batch_size):
        batch = scenes[pos:pos + batch_size]
        payload = [
            {
                "index": s.index,
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "duration": round(s.duration, 2),
                "visual": s.visual,
                "visible_chinese": s.chinese_text,
                "source_meaning": s.source_meaning,
            }
            for s in batch
        ]
        prompt = f"""Write ORIGINAL voice-over narration for a transformed educational/review video.

Target market: {market}
Style: {style}
Primary audience language: natural US English.

GLOBAL UNDERSTANDING:
{summary}

SOURCE AUDIO CONTEXT:
{source}

SCENES:
{json.dumps(payload, ensure_ascii=False)}

Rules:
- Do not translate word-for-word.
- Explain what the viewer sees.
- Strong curiosity hook in index 0.
- Natural American phrasing.
- About 2.0 to 2.4 spoken English words per second.
- Do not fabricate exact technical numbers or claims.
- Avoid repetitive phrases.
- English narration must fit the scene duration.
- Also provide Vietnamese translation for checking.
- Output ONLY JSON array.

[
 {{"index":0,"en_voice":"...","vi_voice":"..."}}
]
"""
        r = _call(lambda: c.interactions.create(
            model=model, input=prompt, store=False
        ))
        arr = _json_array(r.output_text)
        by = {}
        for item in arr:
            try:
                by[int(item.get("index"))] = item
            except Exception:
                pass
        for s in batch:
            item = by.get(s.index, {})
            s.en_voice = str(item.get("en_voice", "")).strip()
            s.vi_voice = str(item.get("vi_voice", "")).strip()
        if progress:
            progress(min(pos + len(batch), total), total)
    return scenes


def _write_wav(path: str, pcm: bytes, rate: int = 24000):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def tts(
    api_key: str,
    model: str,
    voice: str,
    text: str,
    out_path: str,
    direction: str,
):
    c = _client(api_key)
    prompt = f"""Read the transcript exactly as written.
Voice direction: {direction}
Do not add an intro or outro.

Transcript:
{text}
"""
    r = _call(lambda: c.interactions.create(
        model=model,
        input=prompt,
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voice}]},
        store=False,
    ))
    data = r.output_audio.data
    pcm = base64.b64decode(data) if isinstance(data, str) else bytes(data)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out_path, pcm)
    return out_path


def build_tts_chunks(scenes: list[Scene], max_seconds: float = 30.0):
    chunks = []
    current = []
    dur = 0.0

    def flush():
        nonlocal current, dur
        if not current:
            return
        text = " ".join(s.en_voice.strip() for s in current if s.en_voice.strip())
        chunks.append({
            "start": current[0].start,
            "end": current[-1].end,
            "duration": dur,
            "text": text,
            "indexes": [s.index for s in current],
        })
        current = []
        dur = 0.0

    for s in scenes:
        if current and dur + s.duration > max_seconds:
            flush()
        current.append(s)
        dur += s.duration
    flush()
    return chunks


def translate_srt_file(
    api_key: str,
    model: str,
    source_path: str,
    output_path: str,
    target_language: str = "English (US)",
    custom_prompt: str = "",
) -> str:
    """Translate subtitle text while preserving timestamps and cue count."""
    from .subtitle_engine import parse_srt

    src = Path(source_path)
    if not src.exists():
        raise GeminiError(f"Không tìm thấy subtitle: {source_path}")
    cues = parse_srt(src.read_text(encoding='utf-8-sig', errors='replace'))
    if not cues:
        raise GeminiError("Không đọc được cue SRT nào để dịch.")

    c = _client(api_key)
    translated: dict[int, str] = {}
    batch_size = 80
    for pos in range(0, len(cues), batch_size):
        batch = cues[pos:pos + batch_size]
        payload = [
            {"index": pos + i, "text": text}
            for i, (_, _, text) in enumerate(batch)
        ]
        prompt = f"""Translate subtitle lines to {target_language}.
Keep meaning natural for spoken/video subtitles. Preserve names and technical terms.
Do not add facts. Do not merge or split cue indexes.
{custom_prompt.strip()}

Return ONLY JSON array:
[{{"index":0,"text":"translated subtitle"}}]

INPUT:
{json.dumps(payload, ensure_ascii=False)}
"""
        r = _call(lambda: c.interactions.create(model=model, input=prompt, store=False))
        arr = _json_array(r.output_text)
        for item in arr:
            try:
                translated[int(item.get('index'))] = str(item.get('text', '')).strip()
            except Exception:
                pass

    def srt_ts(sec: float) -> str:
        ms = int(round(max(0, sec) * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    blocks = []
    for i, (start, end, text) in enumerate(cues):
        out_text = translated.get(i, text)
        blocks.append(f"{i+1}\n{srt_ts(start)} --> {srt_ts(end)}\n{out_text}\n")
    Path(output_path).write_text('\n'.join(blocks), encoding='utf-8-sig')
    return output_path
