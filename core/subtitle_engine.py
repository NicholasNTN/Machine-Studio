from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import re
import textwrap

from .models import SubtitleStyle
from .subtitle_sizing import ass_font_size


PRESETS: dict[str, SubtitleStyle] = {
    "Documentary Clean": SubtitleStyle(
        preset_name="Documentary Clean", font_name="Arial", font_size=48,
        primary_color="#FFFFFF", outline_color="#000000", bold=True,
        outline=3.0, shadow=1.0, y_percent=86, max_chars_per_line=34,
    ),
    "Classic Yellow": SubtitleStyle(
        preset_name="Classic Yellow", font_name="Arial", font_size=48,
        primary_color="#FFE600", outline_color="#000000", bold=True,
        outline=3.5, shadow=1.0, y_percent=86,
    ),
    "Cinema Gold": SubtitleStyle(
        preset_name="Cinema Gold", font_name="Georgia", font_size=46,
        primary_color="#F6D77A", outline_color="#201500", bold=True,
        outline=2.5, shadow=2.0, y_percent=87,
    ),
    "News White": SubtitleStyle(
        preset_name="News White", font_name="Arial", font_size=44,
        primary_color="#FFFFFF", outline_color="#000000", bold=True,
        outline=2.0, shadow=0.0, background_box=True,
        background_color="#111111", background_opacity=72, y_percent=88,
    ),
    "Factory Orange": SubtitleStyle(
        preset_name="Factory Orange", font_name="Arial", font_size=48,
        primary_color="#FFB000", outline_color="#111111", bold=True,
        outline=3.0, shadow=1.0, y_percent=86,
    ),
    "Tech Cyan": SubtitleStyle(
        preset_name="Tech Cyan", font_name="Arial", font_size=47,
        primary_color="#35E9FF", outline_color="#00141A", bold=True,
        outline=3.0, shadow=2.0, y_percent=86,
    ),
    "Neon Green": SubtitleStyle(
        preset_name="Neon Green", font_name="Arial", font_size=47,
        primary_color="#45FF45", outline_color="#001000", bold=True,
        outline=3.0, shadow=2.0, y_percent=86,
    ),
    "Neon Pink": SubtitleStyle(
        preset_name="Neon Pink", font_name="Arial", font_size=47,
        primary_color="#FF4BC8", outline_color="#200018", bold=True,
        outline=3.0, shadow=2.0, y_percent=86,
    ),
    "Neon Purple": SubtitleStyle(
        preset_name="Neon Purple", font_name="Arial", font_size=47,
        primary_color="#C85CFF", outline_color="#160020", bold=True,
        outline=3.0, shadow=2.0, y_percent=86,
    ),
    "Bold Red": SubtitleStyle(
        preset_name="Bold Red", font_name="Arial", font_size=50,
        primary_color="#FF4040", outline_color="#FFFFFF", bold=True,
        outline=2.0, shadow=1.0, y_percent=85,
    ),
    "Minimal White": SubtitleStyle(
        preset_name="Minimal White", font_name="Arial", font_size=42,
        primary_color="#FFFFFF", outline_color="#000000", bold=False,
        outline=1.5, shadow=0.0, y_percent=88,
    ),
    "Shorts Punch": SubtitleStyle(
        preset_name="Shorts Punch", font_name="Arial", font_size=58,
        primary_color="#FFFFFF", outline_color="#000000", bold=True,
        outline=4.5, shadow=0.5, y_percent=78, max_chars_per_line=24,
        uppercase=True,
    ),
    "Box White": SubtitleStyle(
        preset_name="Box White", font_name="Arial", font_size=44,
        primary_color="#111111", outline_color="#FFFFFF", bold=True,
        outline=0.0, shadow=0.0, background_box=True,
        background_color="#FFFFFF", background_opacity=92, y_percent=87,
    ),
    "Box Black": SubtitleStyle(
        preset_name="Box Black", font_name="Arial", font_size=44,
        primary_color="#FFFFFF", outline_color="#000000", bold=True,
        outline=0.0, shadow=0.0, background_box=True,
        background_color="#000000", background_opacity=78, y_percent=87,
    ),
    "Karaoke Blue": SubtitleStyle(
        preset_name="Karaoke Blue", font_name="Arial", font_size=48,
        primary_color="#6CB7FF", outline_color="#00172E", bold=True,
        outline=3.0, shadow=1.0, y_percent=86,
    ),
    "Elegant": SubtitleStyle(
        preset_name="Elegant", font_name="Times New Roman", font_size=46,
        primary_color="#F4EFE5", outline_color="#261F1A", bold=False,
        italic=True, outline=2.0, shadow=1.0, y_percent=87,
    ),
}

# Original Machine Studio presets using only fields supported by Preview/ASS.
_EXTRA_PRESET_SPECS = {
    "CLEAN": [("Clean White", "#FFFFFF", "#000000"), ("Clean Bold", "#FFFFFF", "#101010"), ("White Shadow", "#FFFFFF", "#303030"), ("Black Box", "#FFFFFF", "#000000"), ("White Box", "#111111", "#FFFFFF"), ("Minimal Lower Third", "#F5F5F5", "#151515")],
    "TRENDING / SOCIAL": [("Bold Yellow", "#FFE600", "#000000"), ("Yellow Punch", "#FFD400", "#151515"), ("Yellow Black Stroke", "#FFF000", "#000000"), ("TikTok White", "#FFFFFF", "#121212"), ("TikTok Yellow", "#FFE45B", "#161616"), ("Viral Bold", "#FFFFFF", "#000000"), ("Creator Pop", "#FF70B7", "#291020"), ("Punch Caption", "#FFFFFF", "#1B1B1B"), ("Modern Highlight", "#72E6FF", "#09222A"), ("Keyword Highlight", "#FFF36A", "#251E00")],
    "GLOW / NEON": [("Neon Yellow", "#F7FF45", "#5A5600"), ("Neon Cyan", "#30F4FF", "#004C52"), ("Neon Blue", "#4B8DFF", "#071B4A"), ("Neon Purple", "#C65CFF", "#35004F"), ("Neon Red", "#FF4E5E", "#520008"), ("Soft Glow", "#E8F1FF", "#52709D")],
    "CINEMATIC": [("Cinema White", "#F4F1E8", "#17130E"), ("Film Subtitle", "#EEE9DD", "#191919"), ("Dramatic", "#FFFFFF", "#300000"), ("Mystery", "#C9D1E8", "#080B13"), ("Documentary Gold", "#E6C86E", "#231A00"), ("Trailer Bold", "#FFFFFF", "#000000")],
    "KARAOKE / WORD POP": [("Karaoke Yellow", "#FFE600", "#1C1800"), ("Karaoke Cyan", "#3DEBFF", "#002C32"), ("Karaoke Green", "#62F26D", "#06310A"), ("Karaoke Pink", "#FF6BC7", "#3A0827"), ("Word Pop Yellow", "#FFE85C", "#211B00"), ("Word Pop White", "#FFFFFF", "#111111"), ("Word Pop Cyan", "#60EFFF", "#003138"), ("Word Pop Orange", "#FF9C43", "#3D1900")],
    "TECH / MACHINE CHANNEL": [("Industrial Yellow", "#FFD21F", "#191600"), ("Engineering Cyan", "#40DFF5", "#002B31"), ("Factory Orange", "#FF9D2E", "#301600"), ("Machine White", "#F2F5F7", "#20282D"), ("Blueprint Blue", "#7AC5FF", "#082542"), ("Warning Red", "#FF4B42", "#3A0500"), ("Steel Caption", "#D0D8DE", "#273139"), ("Construction Yellow", "#FFC928", "#2B2300")],
    "NEWS / INFO": [("Breaking Red", "#FFFFFF", "#A60000"), ("Info Blue", "#FFFFFF", "#074EA3"), ("Statistic Yellow", "#FFE45C", "#172033"), ("Before Label", "#FFFFFF", "#9B2631"), ("After Label", "#FFFFFF", "#197648")],
}

PRESET_CATEGORIES = {name: "ORIGINAL" for name in PRESETS}
for category, specs in _EXTRA_PRESET_SPECS.items():
    for index, (name, primary, outline_color) in enumerate(specs):
        boxed = name in {"Black Box", "White Box", "Breaking Red", "Info Blue", "Before Label", "After Label"}
        animation = "Karaoke" if name.startswith("Karaoke") else "Word Pop Sync" if name.startswith("Word Pop") else "Pop" if category == "TRENDING / SOCIAL" else "Không"
        PRESETS[name] = SubtitleStyle(preset_name=name, font_name="Arial", font_size=52 if ("Bold" in name or "Punch" in name) else 46, primary_color=primary, outline_color=outline_color, bold=not name.startswith("Film"), outline=0.0 if boxed else 3.0, shadow=2.0 if "Neon" in name or "Glow" in name else 1.0, background_box=boxed, background_color=outline_color, background_opacity=86, y_percent=84 if category in {"TRENDING / SOCIAL", "KARAOKE / WORD POP"} else 87, max_chars_per_line=28 if category == "TRENDING / SOCIAL" else 34, animation=animation, karaoke_color="#FFE600")
        PRESET_CATEGORIES[name] = category


def clone_preset(name: str) -> SubtitleStyle:
    style = PRESETS.get(name) or PRESETS["Documentary Clean"]
    return SubtitleStyle(**asdict(style))


def list_presets() -> list[str]:
    return list(PRESETS.keys())


def preset_category(name: str) -> str:
    return PRESET_CATEGORIES.get(name, "ORIGINAL")


def _hex_to_ass(hex_color: str, opacity: int = 100) -> str:
    s = (hex_color or "#FFFFFF").lstrip("#")
    if len(s) != 6:
        s = "FFFFFF"
    r, g, b = s[0:2], s[2:4], s[4:6]
    # ASS alpha: 00 opaque, FF transparent.
    opacity = max(0, min(100, int(opacity)))
    alpha = round(255 * (1 - opacity / 100))
    return f"&H{alpha:02X}{b}{g}{r}"


def _hex_to_ass_inline(hex_color: str) -> str:
    s = (hex_color or "#FFFFFF").lstrip("#")
    if len(s) != 6:
        s = "FFFFFF"
    r, g, b = s[0:2], s[2:4], s[4:6]
    return f"&H{b}{g}{r}&"


def _ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _parse_srt_time(value: str) -> float:
    value = value.strip().replace('.', ',')
    h, m, rest = value.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(text: str) -> list[tuple[float, float, str]]:
    text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not text:
        return []
    chunks = re.split(r"\n\s*\n", text)
    cues = []
    time_re = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
    )
    for chunk in chunks:
        lines = [x for x in chunk.split('\n')]
        t_idx = next((i for i, x in enumerate(lines) if '-->' in x), None)
        if t_idx is None:
            continue
        m = time_re.search(lines[t_idx])
        if not m:
            continue
        try:
            start, end = _parse_srt_time(m.group(1)), _parse_srt_time(m.group(2))
        except Exception:
            continue
        body = '\n'.join(lines[t_idx + 1:]).strip()
        if body:
            cues.append((start, end, body))
    return cues



def _clean_caption_text(text: str, uppercase: bool = False) -> str:
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    text = text.replace("{", "").replace("}", "")
    text = " ".join(text.replace("\n", " ").replace(r"\N", " ").split())
    return text.upper() if uppercase else text


def split_text_single_line(text: str, max_chars: int) -> list[str]:
    """Greedy phrase splitter that NEVER returns embedded newlines.

    It keeps whole words where possible. For CJK/no-space text it falls back
    to character chunks. This is intended for subtitle cue segmentation,
    not visual line wrapping.
    """
    text = _clean_caption_text(text, False)
    max_chars = max(8, int(max_chars or 32))
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    # CJK / no-space fallback.
    if " " not in text:
        return [
            text[i:i + max_chars].strip()
            for i in range(0, len(text), max_chars)
            if text[i:i + max_chars].strip()
        ]

    words = text.split()
    chunks = []
    current = ""

    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            current = ""

        # Extremely long token: hard split only as last resort.
        if len(word) > max_chars:
            while len(word) > max_chars:
                chunks.append(word[:max_chars])
                word = word[max_chars:]
            current = word
        else:
            current = word

    if current:
        chunks.append(current.strip())

    # Prefer punctuation-balanced chunks when a very short tail is created.
    if len(chunks) >= 2 and len(chunks[-1]) < max(6, max_chars // 4):
        merged = f"{chunks[-2]} {chunks[-1]}".strip()
        if len(merged) <= max_chars + max(4, max_chars // 5):
            # Split the merged phrase closer to the middle.
            merged_words = merged.split()
            best = None
            for i in range(1, len(merged_words)):
                left = " ".join(merged_words[:i])
                right = " ".join(merged_words[i:])
                if len(left) <= max_chars and len(right) <= max_chars:
                    score = abs(len(left) - len(right))
                    if best is None or score < best[0]:
                        best = (score, left, right)
            if best:
                chunks[-2], chunks[-1] = best[1], best[2]

    return [x for x in chunks if x]


def split_single_line_cues(
    cues: list[tuple[float, float, str]],
    max_chars: int,
    uppercase: bool = False,
) -> list[tuple[float, float, str]]:
    """Split each timed cue into sequential one-line cues.

    The original cue's start/end are preserved as the outer boundary.
    Child cue durations are allocated proportionally to text/word weight,
    so the whole subtitle still stays inside the exact voice time window.
    """
    out = []
    max_chars = max(8, int(max_chars or 32))

    for start, end, text in cues:
        start = float(start)
        end = float(end)
        if end <= start:
            continue

        clean = _clean_caption_text(text, uppercase)
        chunks = split_text_single_line(clean, max_chars)
        if not chunks:
            continue
        if len(chunks) == 1:
            out.append((start, end, chunks[0]))
            continue

        duration = end - start

        def weight(chunk: str) -> float:
            # Word count tracks English/Vietnamese speech fairly well.
            # Character count is better for CJK/no-space strings.
            if " " in chunk:
                return max(1.0, len(chunk.split()) + len(chunk) / 35.0)
            return max(1.0, len(chunk))

        weights = [weight(c) for c in chunks]
        total_w = sum(weights) or float(len(chunks))
        cursor = start

        for i, (chunk, w) in enumerate(zip(chunks, weights)):
            if i == len(chunks) - 1:
                cue_end = end
            else:
                cue_end = cursor + duration * (w / total_w)
                # avoid a zero-duration cue due to rounding
                cue_end = max(cursor + 0.08, min(end, cue_end))

            out.append((cursor, cue_end, chunk))
            cursor = cue_end

    return out


def write_srt_cues(
    cues: list[tuple[float, float, str]],
    output_path: str,
) -> str:
    def ts(seconds: float) -> str:
        ms = max(0, int(round(float(seconds) * 1000)))
        h, rem = divmod(ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = []
    for i, (start, end, text) in enumerate(cues, 1):
        body = _clean_caption_text(text, False)
        if not body or end <= start:
            continue
        blocks.append(
            f"{i}\n{ts(start)} --> {ts(end)}\n{body}\n"
        )

    Path(output_path).write_text(
        "\n".join(blocks),
        encoding="utf-8-sig",
    )
    return output_path


def reflow_srt_single_line(
    path: str,
    max_chars: int,
    uppercase: bool = False,
) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    cues = parse_srt(p.read_text(encoding="utf-8-sig", errors="replace"))
    cues = split_single_line_cues(cues, max_chars, uppercase)
    return write_srt_cues(cues, str(p))


def _wrap_caption(text: str, max_chars: int, uppercase: bool = False) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace('{', r'\{').replace('}', r'\}')
    text = ' '.join(text.replace('\n', ' ').split())
    if uppercase:
        text = text.upper()
    if max_chars <= 0:
        return text
    lines = textwrap.wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False)
    return r'\N'.join(lines or [text])



def _ass_escape_text(value: str) -> str:
    return str(value or "").replace("{", r"\{").replace("}", r"\}")


def _karaoke_body(
    text: str,
    duration_seconds: float,
) -> str:
    words = str(text or "").split()
    if not words:
        return ""
    total_cs = max(len(words), int(round(max(0.10, duration_seconds) * 100)))
    per = max(1, total_cs // len(words))
    remaining = total_cs
    parts = []
    for i, word in enumerate(words):
        cs = remaining if i == len(words) - 1 else min(remaining, per)
        remaining -= cs
        parts.append(r"{\kf" + str(max(1, cs)) + "}" + word)
    return " ".join(parts)


def _typewriter_events(
    start: float,
    end: float,
    text: str,
    x: int,
    y: int,
    duration_ms: int,
) -> list[str]:
    clean = str(text or "")
    if not clean or end <= start:
        return []

    # Cap event count so long captions do not explode the ASS file.
    max_steps = min(28, max(1, len(clean)))
    reveal_duration = min(
        max(0.08, duration_ms / 1000.0),
        max(0.08, (end - start) * 0.72),
    )

    events = []
    for step in range(1, max_steps + 1):
        char_count = max(1, round(len(clean) * step / max_steps))
        part = clean[:char_count]
        ev_start = start + reveal_duration * (step - 1) / max_steps
        ev_end = (
            start + reveal_duration * step / max_steps
            if step < max_steps
            else end
        )
        events.append(
            f"Dialogue: 0,{_ass_time(ev_start)},{_ass_time(ev_end)},"
            f"Default,,0,0,0,,{{\\an5\\pos({x},{y})}}{part}"
        )
    return events



def _word_pop_override(
    style: SubtitleStyle,
    x: int,
    y: int,
    cue_duration: float,
) -> str:
    """Smooth small pop for a single word."""
    peak = max(101, min(125, int(getattr(style, "word_pop_scale", 108))))
    pop_ms = max(60, min(260, int(getattr(style, "word_pop_ms", 110))))
    cue_ms = max(70, int(max(0.07, cue_duration) * 1000))
    pop_ms = min(pop_ms, max(60, int(cue_ms * 0.62)))

    start_scale = 88
    settle = min(
        cue_ms - 10,
        max(pop_ms + 35, int(pop_ms * 1.55)),
    )
    settle = max(pop_ms + 1, settle)

    fade_in = min(45, pop_ms)
    fade_out = min(38, max(18, int(cue_ms * 0.15)))

    return (
        rf"\an5\pos({x},{y})"
        rf"\fscx{start_scale}\fscy{start_scale}"
        rf"\fad({fade_in},{fade_out})"
        rf"\t(0,{pop_ms},\fscx{peak}\fscy{peak})"
        rf"\t({pop_ms},{settle},\fscx100\fscy100)"
    )

def _animation_override(
    style: SubtitleStyle,
    x: int,
    y: int,
    cue_duration: float,
) -> str:
    effect = str(getattr(style, "animation", "Không") or "Không")
    ms = max(60, min(1200, int(getattr(style, "animation_duration_ms", 220))))
    strength = max(10, min(200, int(getattr(style, "animation_strength", 100))))
    amount = strength / 100.0

    base = rf"\an5\pos({x},{y})"
    if effect == "Fade":
        return base + rf"\fad({ms},{min(ms, 180)})"

    if effect == "Slide Up":
        offset = int(90 * amount)
        return (
            rf"\an5\move({x},{y + offset},{x},{y},0,{ms})"
            rf"\fad({min(90, ms)},{min(100, ms)})"
        )

    if effect == "Pop":
        start_scale = max(25, int(62 / max(0.6, amount)))
        overshoot = min(135, int(108 + 8 * amount))
        settle_at = min(ms * 2, ms + 150)
        return (
            base
            + rf"\fscx{start_scale}\fscy{start_scale}"
            + rf"\t(0,{ms},\fscx{overshoot}\fscy{overshoot})"
            + rf"\t({ms},{settle_at},\fscx100\fscy100)"
        )

    if effect == "Bounce":
        offset = int(80 * amount)
        overshoot = min(140, int(112 + 8 * amount))
        return (
            rf"\an5\move({x},{y + offset},{x},{y},0,{ms})"
            rf"\fscx82\fscy82"
            rf"\t(0,{ms},\fscx{overshoot}\fscy{overshoot})"
            rf"\t({ms},{min(ms + 170, ms * 2)},\fscx100\fscy100)"
        )

    return base

def create_ass(
    cues: list[tuple[float, float, str]],
    output_path: str,
    style: SubtitleStyle,
    play_res_x: int = 1080,
    play_res_y: int = 1920,
    overlay_text: str = "",
    overlay_position: str = "Top-left",
    overlay_font_name: str = "Arial",
    overlay_font_size: int = 34,
    overlay_color: str = "#FFFFFF",
    overlay_x_percent: float = 12.0,
    overlay_y_percent: float = 8.0,
    duration: float = 0.0,
    extra_text_layers: list[dict] | None = None,
) -> str:
    play_res_x = max(320, int(play_res_x or 1080))
    play_res_y = max(240, int(play_res_y or 1920))

    primary = _hex_to_ass(style.primary_color, 100)
    secondary = _hex_to_ass(
        getattr(style, "karaoke_color", "#FFE600"),
        100,
    )
    outline = _hex_to_ass(style.outline_color, 100)
    back = _hex_to_ass(style.background_color, style.background_opacity if style.background_box else 0)
    border_style = 3 if style.background_box else 1
    bold = -1 if style.bold else 0
    italic = -1 if style.italic else 0

    # Use absolute position so the vertical placement slider behaves predictably.
    x = int(play_res_x * max(5, min(95, getattr(style, "x_percent", 50))) / 100)
    y = int(play_res_y * max(5, min(95, style.y_percent)) / 100)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{style.font_name},{ass_font_size(style.font_size)},{primary},{secondary},{outline},{back},{bold},{italic},0,0,100,100,0,0,{border_style},{style.outline:.2f},{style.shadow:.2f},5,20,20,20,1
Style: Overlay,{overlay_font_name},{overlay_font_size},{_hex_to_ass(overlay_color,100)},{_hex_to_ass(overlay_color,100)},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,2,1,7,20,20,20,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    events = []

    # UI already derives max_chars_per_line from available pixel width and
    # the FIXED project font size. Do not rescale again here.
    effective_chars = max(8, int(style.max_chars_per_line))

    render_cues = list(cues)
    if getattr(style, "single_line_auto", True):
        render_cues = split_single_line_cues(
            render_cues,
            effective_chars,
            style.uppercase,
        )

    for start, end, text in render_cues:
        if getattr(style, "single_line_auto", True):
            # Absolutely no ASS \N line break in one-line mode.
            body = _clean_caption_text(text, style.uppercase)
        else:
            body = _wrap_caption(text, effective_chars, style.uppercase)

        effect = str(getattr(style, "animation", "Không") or "Không")
        cue_duration = max(0.01, end - start)

        if effect == "Typewriter":
            events.extend(
                _typewriter_events(
                    start,
                    end,
                    body,
                    x,
                    y,
                    int(getattr(style, "animation_duration_ms", 220)),
                )
            )
            continue

        if effect == "Karaoke":
            body = _karaoke_body(body, cue_duration)

        if effect == "Word Pop Sync":
            override = _word_pop_override(
                style,
                x,
                y,
                cue_duration,
            )
        else:
            override = _animation_override(
                style,
                x,
                y,
                cue_duration,
            )
        events.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},"
            f"Default,,0,0,0,,{{{override}}}{body}"
        )

    if overlay_text.strip() and duration > 0:
        ox = int(play_res_x * max(2, min(98, float(overlay_x_percent))) / 100)
        oy = int(play_res_y * max(2, min(98, float(overlay_y_percent))) / 100)
        txt = _wrap_caption(overlay_text, 60, False)
        events.append(
            f"Dialogue: 2,0:00:00.00,{_ass_time(duration)},Overlay,,0,0,0,,{{\\an5\\pos({ox},{oy})}}{txt}"
        )

    # Basic Editor supports multiple independent text layers.
    for layer_index, layer in enumerate(extra_text_layers or []):
        if not isinstance(layer, dict):
            continue
        if not layer.get("enabled", True) or layer.get("type") != "text":
            continue
        text_value = str(layer.get("text", "") or "").strip()
        if not text_value:
            continue

        start = max(0.0, float(layer.get("start", 0.0) or 0.0))
        end = float(layer.get("end", duration or start + 0.1) or 0.0)
        if duration > 0:
            end = min(duration, end)
        if end <= start:
            continue

        tx = int(play_res_x * max(1, min(99, float(layer.get("x", 50.0)))) / 100)
        ty = int(play_res_y * max(1, min(99, float(layer.get("y", 50.0)))) / 100)
        font_name = str(layer.get("font_name", "Arial") or "Arial")
        font_size = max(8, min(240, int(layer.get("font_size", 52) or 52)))
        color = _hex_to_ass_inline(str(layer.get("color", "#FFFFFF") or "#FFFFFF"))
        opacity = max(1, min(100, int(layer.get("opacity", 100) or 100)))
        alpha = round(255 * (1 - opacity / 100))
        body = _wrap_caption(text_value, max(1, int(layer.get("max_chars", 80) or 80)), bool(layer.get("uppercase", False)))
        align = {"Left": 4, "Right": 6}.get(str(layer.get("alignment", "Center")), 5)
        outline_color = _hex_to_ass_inline(str(layer.get("outline_color", "#000000") or "#000000"))
        background_color = _hex_to_ass_inline(str(layer.get("background_color", "#000000") or "#000000"))
        tags = (
            rf"\an{align}\pos({tx},{ty})"
            rf"\fn{font_name}\fs{font_size}"
            rf"\1c{color}\1a&H{alpha:02X}&"
            rf"\3c{outline_color}\bord{max(0, float(layer.get('outline_width', 2))):.1f}"
            rf"\shad{max(0, float(layer.get('shadow', 1))):.1f}"
            rf"\b{1 if layer.get('bold', True) else 0}\i{1 if layer.get('italic', False) else 0}"
            rf"\fscx{max(10, float(layer.get('scale', 100))):.1f}\fscy{max(10, float(layer.get('scale', 100))):.1f}"
            rf"\frz{float(layer.get('rotation', 0)):.1f}"
        )
        if layer.get("background_box", False): tags += rf"\4c{background_color}\4a&H{round(255 * (1 - float(layer.get('background_opacity', 65)) / 100)):02X}&\bord{max(2, float(layer.get('outline_width', 2))):.1f}"
        events.append(
            f"Dialogue: {3 + layer_index},{_ass_time(start)},{_ass_time(end)},"
            f"Overlay,,0,0,0,,{{{tags}}}{body}"
        )

    Path(output_path).write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')
    return output_path


def prepare_ass(
    subtitle_path: str,
    output_path: str,
    style: SubtitleStyle,
    play_res_x: int,
    play_res_y: int,
    overlay_text: str = "",
    overlay_position: str = "Top-left",
    overlay_font_name: str = "Arial",
    overlay_font_size: int = 34,
    overlay_color: str = "#FFFFFF",
    overlay_x_percent: float = 12.0,
    overlay_y_percent: float = 8.0,
    duration: float = 0.0,
    extra_text_layers: list[dict] | None = None,
) -> str:
    cues = []
    path = Path(subtitle_path) if subtitle_path else None
    if path and path.exists():
        if path.suffix.lower() == '.srt':
            cues = parse_srt(path.read_text(encoding='utf-8-sig', errors='replace'))
        elif path.suffix.lower() in {'.ass', '.ssa'}:
            # Existing ASS already includes its own styling. Keep it intact.
            # Custom SRT style controls are intentionally not forced onto imported ASS files.
            return str(path)
        else:
            # Best-effort parse as SRT text.
            cues = parse_srt(path.read_text(encoding='utf-8-sig', errors='replace'))

    return create_ass(
        cues, output_path, style, play_res_x, play_res_y,
        overlay_text=overlay_text,
        overlay_position=overlay_position,
        overlay_font_name=overlay_font_name,
        overlay_font_size=overlay_font_size,
        overlay_color=overlay_color,
        overlay_x_percent=overlay_x_percent,
        overlay_y_percent=overlay_y_percent,
        duration=duration,
        extra_text_layers=extra_text_layers,
    )


def replace_in_srt(path: str, find_text: str, replace_text: str) -> int:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    text = p.read_text(encoding='utf-8-sig', errors='replace')
    count = text.count(find_text)
    if find_text:
        text = text.replace(find_text, replace_text)
        p.write_text(text, encoding='utf-8-sig')
    return count


def save_style(path: str, style: SubtitleStyle):
    Path(path).write_text(json.dumps(asdict(style), ensure_ascii=False, indent=2), encoding='utf-8')


def load_style(path: str) -> SubtitleStyle:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return SubtitleStyle(**data)
