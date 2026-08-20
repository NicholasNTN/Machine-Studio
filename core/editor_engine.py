from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import os
import shutil
import tempfile
import time

from . import ffmpeg_engine as ffm


class EditorError(RuntimeError):
    pass


def clip_duration(clip: dict) -> float:
    return max(
        0.0,
        float(clip.get("source_end", 0.0) or 0.0)
        - float(clip.get("source_start", 0.0) or 0.0),
    )


def total_duration(clips: list[dict]) -> float:
    return sum(clip_duration(c) for c in clips if c.get("enabled", True))


def normalize_clip(clip: dict) -> dict:
    c = dict(clip or {})
    path = str(c.get("path", "") or "")
    c["path"] = path
    c["name"] = str(c.get("name", "") or Path(path).name)
    c["source_start"] = max(0.0, float(c.get("source_start", 0.0) or 0.0))
    c["source_end"] = max(
        c["source_start"] + 0.05,
        float(c.get("source_end", c["source_start"] + 0.05) or 0.0),
    )
    c["enabled"] = bool(c.get("enabled", True))
    c["id"] = str(c.get("id", "") or _clip_id(path))
    return c


def _clip_id(path: str) -> str:
    raw = f"{path}|{time.time_ns()}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:14]


def make_clip(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise EditorError(f"Không tìm thấy video: {path}")
    info = ffm.probe(str(p))
    duration = max(0.05, float(info.get("duration", 0.0) or 0.0))
    return {
        "id": _clip_id(str(p.resolve())),
        "path": str(p.resolve()),
        "name": p.name,
        "source_start": 0.0,
        "source_end": duration,
        "source_duration": duration,
        "enabled": True,
    }


def timeline_ranges(clips: list[dict]) -> list[tuple[float, float]]:
    ranges = []
    cursor = 0.0
    for clip in clips:
        dur = clip_duration(clip) if clip.get("enabled", True) else 0.0
        ranges.append((cursor, cursor + dur))
        cursor += dur
    return ranges


def locate_time(clips: list[dict], global_second: float):
    """Return (clip_index, source_second, clip_global_start)."""
    t = max(0.0, float(global_second or 0.0))
    cursor = 0.0
    for i, clip in enumerate(clips):
        if not clip.get("enabled", True):
            continue
        dur = clip_duration(clip)
        end = cursor + dur
        if t < end or (i == len(clips) - 1 and abs(t - end) < 0.001):
            local = max(0.0, min(dur, t - cursor))
            source_second = float(clip.get("source_start", 0.0)) + local
            return i, source_second, cursor
        cursor = end
    if clips:
        i = len(clips) - 1
        clip = clips[i]
        return i, float(clip.get("source_end", 0.0)), max(0.0, cursor - clip_duration(clip))
    return -1, 0.0, 0.0


def global_time_for_clip_source(clips: list[dict], index: int, source_second: float) -> float:
    ranges = timeline_ranges(clips)
    if not (0 <= index < len(clips)):
        return 0.0
    clip = clips[index]
    start = float(clip.get("source_start", 0.0))
    local = max(0.0, min(clip_duration(clip), float(source_second) - start))
    return ranges[index][0] + local


def split_clip(clips: list[dict], index: int, source_second: float) -> int:
    if not (0 <= index < len(clips)):
        raise EditorError("Chưa chọn clip để cắt.")
    clip = normalize_clip(clips[index])
    cut = float(source_second)
    start = float(clip["source_start"])
    end = float(clip["source_end"])
    if cut <= start + 0.08 or cut >= end - 0.08:
        raise EditorError("Điểm cắt quá sát đầu/cuối clip.")

    left = dict(clip)
    right = dict(clip)
    left["id"] = _clip_id(left["path"])
    right["id"] = _clip_id(right["path"])
    left["source_end"] = cut
    right["source_start"] = cut
    left["name"] = f"{Path(clip['path']).stem} A"
    right["name"] = f"{Path(clip['path']).stem} B"
    clips[index:index + 1] = [left, right]
    return index + 1


def reorder_clip(clips: list[dict], source_index: int, target_index: int) -> int:
    if not (0 <= source_index < len(clips)):
        return source_index
    target_index = max(0, min(len(clips) - 1, int(target_index)))
    item = clips.pop(source_index)
    clips.insert(target_index, item)
    return target_index


def trim_clip(clip: dict, source_start: float, source_end: float) -> dict:
    c = normalize_clip(clip)
    full = float(c.get("source_duration", 0.0) or 0.0)
    if full <= 0:
        try:
            full = float(ffm.probe(c["path"]).get("duration", 0.0) or 0.0)
        except Exception:
            full = max(float(c["source_end"]), source_end)

    start = max(0.0, min(full - 0.05, float(source_start)))
    end = max(start + 0.05, min(full, float(source_end)))
    c["source_start"] = start
    c["source_end"] = end
    c["source_duration"] = full
    return c


def _safe_even(value: int) -> int:
    value = max(2, int(value))
    return value if value % 2 == 0 else value - 1


def render_timeline(
    clips: list[dict],
    output_path: str,
    *,
    target_width: int | None = None,
    target_height: int | None = None,
    preview: bool = False,
    log=None,
    process_holder=None,
) -> str:
    """Render trimmed/reordered clips into one normalized H.264/AAC timeline."""
    active = [normalize_clip(c) for c in clips if c.get("enabled", True) and clip_duration(c) >= 0.05]
    if not active:
        raise EditorError("Timeline chưa có clip.")

    for clip in active:
        if not Path(clip["path"]).exists():
            raise EditorError(f"File clip không tồn tại: {clip['path']}")

    first_info = ffm.probe(active[0]["path"])
    if target_width and target_height:
        out_w = _safe_even(target_width)
        out_h = _safe_even(target_height)
    else:
        out_w = _safe_even(first_info.get("width") or 1080)
        out_h = _safe_even(first_info.get("height") or 1920)

    # Preview proxy should be quick and light.
    if preview:
        max_w = 720
        if out_w > max_w:
            ratio = max_w / out_w
            out_w = _safe_even(max_w)
            out_h = _safe_even(out_h * ratio)

    ffmpeg = ffm.find_binary("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-y"]
    infos = []
    for clip in active:
        info = ffm.probe(clip["path"])
        infos.append(info)
        cmd += ["-i", clip["path"]]

    filters = []
    concat_inputs = []

    for i, (clip, info) in enumerate(zip(active, infos)):
        start = float(clip["source_start"])
        end = float(clip["source_end"])
        dur = max(0.05, end - start)

        filters.append(
            f"[{i}:v]"
            f"trim=start={start:.6f}:end={end:.6f},"
            "setpts=PTS-STARTPTS,"
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
            f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black,"
            "setsar=1,fps=30,format=yuv420p"
            f"[v{i}]"
        )

        if info.get("has_audio"):
            filters.append(
                f"[{i}:a]"
                f"atrim=start={start:.6f}:end={end:.6f},"
                "asetpts=PTS-STARTPTS,"
                "aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo"
                f"[a{i}]"
            )
        else:
            filters.append(
                "anullsrc=channel_layout=stereo:sample_rate=48000,"
                f"atrim=duration={dur:.6f},asetpts=PTS-STARTPTS[a{i}]"
            )

        concat_inputs.append(f"[v{i}][a{i}]")

    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(active)}:v=1:a=1[vout][aout]"
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    preset = "ultrafast" if preview else "veryfast"
    crf = "27" if preview else "19"

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", crf,
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        output_path,
    ]

    if log:
        log(
            f"[EDITOR] Render timeline: {len(active)} clip | "
            f"{out_w}x{out_h} | duration={total_duration(active):.2f}s"
        )

    ffm.run(
        cmd,
        log=log,
        process_holder=process_holder,
        low_priority=preview,
    )

    target = Path(output_path)
    if not target.exists() or target.stat().st_size < 1024:
        raise EditorError("Không render được timeline.")
    return str(target)


def make_text_layer(
    text: str,
    total_seconds: float,
    *,
    x: float = 50.0,
    y: float = 50.0,
) -> dict:
    return {
        "id": _clip_id("text"),
        "type": "text",
        "enabled": True,
        "text": str(text or "Text"),
        "x": float(x),
        "y": float(y),
        "font_name": "Arial",
        "font_size": 52,
        "color": "#FFFFFF",
        "opacity": 100,
        "start": 0.0,
        "end": max(0.1, float(total_seconds or 0.1)),
    }


def make_image_layer(
    path: str,
    total_seconds: float,
    *,
    x: float = 50.0,
    y: float = 50.0,
) -> dict:
    return {
        "id": _clip_id("image"),
        "type": "image",
        "enabled": True,
        "path": str(Path(path).resolve()),
        "x": float(x),
        "y": float(y),
        "scale": 20.0,
        "opacity": 100,
        "start": 0.0,
        "end": max(0.1, float(total_seconds or 0.1)),
    }


def layer_active(layer: dict, second: float) -> bool:
    if not layer.get("enabled", True):
        return False
    start = float(layer.get("start", 0.0) or 0.0)
    end = float(layer.get("end", 1e12) or 1e12)
    return start <= float(second) < end
