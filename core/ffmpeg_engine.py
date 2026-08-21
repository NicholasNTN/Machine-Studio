from __future__ import annotations

from pathlib import Path
import subprocess
import shutil
import json
import os
import math
import tempfile
import re
import datetime

from .models import Scene, ExportOptions
from . import subtitle_engine
from editor.blur_zone import source_zone_canvas_rect


class FFmpegError(RuntimeError):
    pass


def app_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_binary(name: str) -> str:
    exe = f"{name}.exe" if os.name == "nt" else name
    local = app_root() / "tools" / exe
    if local.exists():
        return str(local)
    p = shutil.which(name)
    if p:
        return p
    raise FFmpegError(
        f"Không tìm thấy {exe}. Copy {exe} vào thư mục tools hoặc thêm FFmpeg vào PATH."
    )


def _flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _command_text(cmd) -> str:
    return " ".join(f'"{x}"' if any(ch.isspace() for ch in str(x)) else str(x) for x in cmd)


def append_render_log(log_file, text: str):
    if not log_file:
        return
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(str(text))
        if not str(text).endswith("\n"):
            handle.write("\n")
        handle.flush()


def begin_export_log(log_file, *, sequence_id="", sequence_name="", input_path="", output_path=""):
    append_render_log(log_file, "\n" + "=" * 50)
    append_render_log(log_file, "EXPORT START")
    append_render_log(log_file, f"timestamp={datetime.datetime.now().astimezone().isoformat()}")
    append_render_log(log_file, f"sequence_id={sequence_id}")
    append_render_log(log_file, f"sequence_name={sequence_name}")
    append_render_log(log_file, f"input={input_path}")
    append_render_log(log_file, f"output={output_path}")
    append_render_log(log_file, "=" * 50)


def run(cmd: list[str], log=None, process_holder=None, low_priority: bool = False, log_file=None):
    command = _command_text(cmd)
    if log:
        log(command)
    log_handle = None
    p = None
    try:
        if log_file:
            path = Path(log_file); path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = path.open("a", encoding="utf-8", errors="replace")
            log_handle.write(f"FULL FFMPEG COMMAND\n{command}\n"); log_handle.flush()
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
            creationflags=(_flags() | (getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0) if low_priority and os.name == "nt" else 0)),
        )
        if process_holder is not None: process_holder["process"] = p
        lines = []
        assert p.stdout is not None
        for line in p.stdout:
            lines.append(line)
            if log: log(line.rstrip())
            if log_handle:
                log_handle.write(line); log_handle.flush()
        rc = p.wait()
        if log_handle:
            log_handle.write(f"return_code={rc}\n{'EXPORT FAILED' if rc != 0 else 'EXPORT SUCCESS'}\n"); log_handle.flush()
    finally:
        if p is not None and p.stdout is not None: p.stdout.close()
        if process_holder is not None: process_holder["process"] = None
        if log_handle: log_handle.close()
    if rc != 0:
        raise FFmpegError("\n".join(lines[-60:]))
    return "\n".join(lines)


def _normalize_input_path(path: str) -> str:
    raw = str(path or "").strip().strip('"')
    if not raw:
        raise FFmpegError("Đường dẫn video đang rỗng.")

    p = Path(raw).expanduser()

    # Resolve when possible, but don't fail only because resolve() is blocked.
    try:
        p = p.resolve(strict=False)
    except Exception:
        p = Path(os.path.abspath(raw))

    if not p.exists():
        raise FFmpegError(f"Không tìm thấy file video:\n{p}")

    if not p.is_file():
        raise FFmpegError(
            "Đường dẫn đang chọn không phải là file video.\n"
            f"Đường dẫn hiện tại:\n{p}"
        )

    # Python-level read test. This gives a much clearer Windows permission error.
    try:
        with open(p, "rb") as fh:
            fh.read(1)
    except PermissionError as e:
        raise FFmpegError(
            "Windows không cho phép đọc file video nguồn.\n\n"
            f"File:\n{p}\n\n"
            "Cách xử lý nhanh:\n"
            "1) Copy video sang một thư mục thường như D:\\Video\\ hoặc Desktop.\n"
            "2) Không đặt video trong thư mục đang bị OneDrive/antivirus khóa.\n"
            "3) Nếu file vừa tải về, chuột phải > Properties > Unblock (nếu có).\n"
            "4) Đóng app khác đang giữ độc quyền file rồi thử lại."
        ) from e
    except OSError as e:
        raise FFmpegError(f"Không thể mở file video:\n{p}\n\n{e}") from e

    return str(p)


def probe(path: str) -> dict:
    input_path = _normalize_input_path(path)
    ffprobe = find_binary("ffprobe")

    cmd = [
        ffprobe, "-hide_banner", "-v", "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,width,height,r_frame_rate,codec_name",
        "-of", "json",
        input_path,
    ]

    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_flags(),
        )
    except PermissionError as e:
        raise FFmpegError(
            "Windows chặn không cho chạy ffprobe.exe.\n\n"
            f"ffprobe:\n{ffprobe}\n\n"
            "Hãy thử:\n"
            "- Chuột phải ffprobe.exe > Properties > Unblock (nếu có).\n"
            "- Kiểm tra Windows Security/antivirus có chặn file không.\n"
            "- Hoặc cài FFmpeg vào PATH và xóa bản ffprobe.exe bị chặn trong thư mục tools."
        ) from e
    except OSError as e:
        raise FFmpegError(
            f"Không chạy được ffprobe:\n{ffprobe}\n\n{e}"
        ) from e

    if p.returncode != 0:
        err = (p.stderr or "").strip()

        # Give actionable error when ffprobe itself says Permission denied.
        if "permission denied" in err.lower():
            raise FFmpegError(
                "FFprobe bị từ chối quyền đọc video.\n\n"
                f"Video:\n{input_path}\n\n"
                f"FFprobe:\n{ffprobe}\n\n"
                f"Chi tiết:\n{err}\n\n"
                "Thử copy video sang D:\\Video\\test.mp4 rồi chọn lại. "
                "Nếu video ở ổ mạng/OneDrive/thư mục bảo vệ, hãy dùng file local trước."
            )

        raise FFmpegError(
            "FFprobe không đọc được video.\n\n"
            f"Video:\n{input_path}\n\n"
            f"FFprobe:\n{ffprobe}\n\n"
            f"Chi tiết:\n{err or 'Unknown ffprobe error'}"
        )

    try:
        data = json.loads(p.stdout)
    except Exception as e:
        raise FFmpegError(
            "FFprobe chạy nhưng trả dữ liệu không hợp lệ.\n"
            f"Video: {input_path}\n\nOutput:\n{p.stdout[:2000]}"
        ) from e

    streams = data.get("streams", [])
    v = next((x for x in streams if x.get("codec_type") == "video"), {})
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "has_audio": any(x.get("codec_type") == "audio" for x in streams),
        "width": int(v.get("width") or 0),
        "height": int(v.get("height") or 0),
        "codec": v.get("codec_name", ""),
        "normalized_path": input_path,
    }


_NVENC_RUNTIME_OK = None


def nvenc_runtime_available() -> bool:
    """Encoder listing alone is not enough: FFmpeg may expose nvenc while the
    NVIDIA driver/CUDA runtime is unavailable. Probe one tiny frame once.
    """
    global _NVENC_RUNTIME_OK
    if _NVENC_RUNTIME_OK is not None:
        return bool(_NVENC_RUNTIME_OK)
    try:
        if "h264_nvenc" not in available_encoders():
            _NVENC_RUNTIME_OK = False
            return False
        ffmpeg = find_binary("ffmpeg")
        p = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "color=black:s=64x64:d=0.1",
             "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=_flags(), timeout=5,
        )
        _NVENC_RUNTIME_OK = (p.returncode == 0)
    except Exception:
        _NVENC_RUNTIME_OK = False
    return bool(_NVENC_RUNTIME_OK)


def available_encoders() -> str:
    ffmpeg = find_binary("ffmpeg")
    p = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=_flags(),
    )
    return p.stdout or ""


def choose_video_encoder(codec: str, encoder_mode: str) -> list[str]:
    encoders = available_encoders()
    mode = (encoder_mode or "").upper()
    wants_gpu = "GPU" in mode or "AUTO" in mode
    gpu_ok = wants_gpu and nvenc_runtime_available()
    c = (codec or "Auto").upper().replace(".", "").replace("-", "")

    if c == "AUTO":
        c = "H264"

    if c in ("AV1",):
        if gpu_ok and "av1_nvenc" in encoders:
            return ["-c:v", "av1_nvenc", "-preset", "p5", "-cq", "28"]
        if "libsvtav1" in encoders:
            return ["-c:v", "libsvtav1", "-preset", "8", "-crf", "30"]
        if "libaom-av1" in encoders:
            return ["-c:v", "libaom-av1", "-cpu-used", "6", "-crf", "32", "-b:v", "0"]
        c = "H264"

    if c in ("H265", "HEVC"):
        if gpu_ok and "hevc_nvenc" in encoders:
            return ["-c:v", "hevc_nvenc", "-preset", "p5", "-cq", "23"]
        return ["-c:v", "libx265", "-preset", "medium", "-crf", "24"]

    if gpu_ok and "h264_nvenc" in encoders:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "21"]



def extract_preview_still(
    video_path: str,
    out_path: str,
    *,
    at_seconds: float = 0.05,
    width: int = 960,
) -> str:
    """Extract a cached still so Preview is visible before Play is pressed."""
    source = _normalize_input_path(video_path)
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # A previously generated still is instantaneous.
    if target.exists() and target.stat().st_size > 1000:
        return str(target)

    ffmpeg = find_binary("ffmpeg")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-ss", f"{max(0.0, float(at_seconds)):.3f}",
        "-i", source,
        "-frames:v", "1",
        "-vf", f"scale={max(320, int(width))}:-2",
        "-q:v", "4",
        str(target),
    ]
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=_flags(),
        timeout=20,
    )
    if p.returncode != 0 or not target.exists():
        raise FFmpegError(
            "Không tạo được frame Preview đầu tiên."
        )
    return str(target)

def extract_frames(video_path: str, out_dir: str, interval: float = 6.0, width: int = 960):
    info = probe(video_path)
    video_path = info.get("normalized_path", video_path)
    dur = info["duration"]
    if dur <= 0:
        raise FFmpegError("Không đọc được duration.")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for p in out.glob("frame_*.jpg"):
        p.unlink()

    ffmpeg = find_binary("ffmpeg")
    interval = max(2.0, float(interval))
    run([
        ffmpeg, "-y", "-i", video_path,
        "-vf", f"fps=1/{interval},scale={width}:-2",
        "-q:v", "5",
        str(out / "frame_%05d.jpg"),
    ])
    frames = sorted(out.glob("frame_*.jpg"))
    scenes = []
    for i, frame in enumerate(frames):
        start = i * interval
        end = min(dur, (i + 1) * interval)
        scenes.append(Scene(i, start, end, str(frame)))
    return scenes


def extract_audio(video_path: str, out_path: str) -> str:
    info = probe(video_path)
    video_path = info.get("normalized_path", video_path)
    if not info["has_audio"]:
        return ""
    ffmpeg = find_binary("ffmpeg")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    run([
        ffmpeg, "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", out_path,
    ])
    return out_path


def _srt_ts(sec: float) -> str:
    ms = int(round(max(0, sec) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(scenes: list[Scene], out_path: str, field: str = "en_voice") -> str:
    blocks = []
    n = 1
    for s in scenes:
        text = str(getattr(s, field, "") or "").strip()
        if not text:
            continue
        blocks.append(
            f"{n}\n{_srt_ts(s.start)} --> {_srt_ts(s.end)}\n{text}\n"
        )
        n += 1
    Path(out_path).write_text("\n".join(blocks), encoding="utf-8")
    return out_path


def _atempo_chain(speed: float) -> str:
    speed = max(0.125, min(16.0, speed))
    factors = []
    remain = speed
    while remain > 2.0:
        factors.append(2.0)
        remain /= 2.0
    while remain < 0.5:
        factors.append(0.5)
        remain /= 0.5
    factors.append(remain)
    return ",".join(f"atempo={x:.5f}" for x in factors)


def parse_resolution(value: str):
    if not value or value == "Original":
        return None
    m = re.search(r"(\d{3,5})\s*x\s*(\d{3,5})", str(value), flags=re.I)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _escape_sub_path(path: str) -> str:
    p = Path(path).resolve().as_posix()
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")
    return p


def _audio_duration(path: str) -> float:
    ffprobe = find_binary("ffprobe")
    p = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", creationflags=_flags(),
    )
    try:
        return float((p.stdout or "0").strip())
    except Exception:
        return 0.0


def _safe_volume(value: float) -> float:
    return max(0.0, min(3.0, float(value)))


def safe_boxblur_radii(width: int, height: int, desired_radius: int) -> tuple[int, int]:
    """Clamp luma/chroma radii for a YUV420 crop (FFmpeg uses strict limits)."""
    minimum = max(0, min(int(width), int(height)))
    desired = max(0, int(desired_radius))
    max_luma = max(0, (minimum - 1) // 2)
    max_chroma = max(0, (minimum - 1) // 4)
    return min(desired, max_luma), min(desired, max_chroma)


def safe_blur_crop_rect(x, y, width, height, output_width, output_height) -> tuple[int, int, int, int]:
    """Return an in-bounds, even YUV420 crop of at least 2x2 pixels."""
    out_w = max(2, int(output_width)); out_h = max(2, int(output_height))
    x = max(0, min(out_w - 2, int(round(x)))); y = max(0, min(out_h - 2, int(round(y))))
    x -= x % 2; y -= y % 2
    width = max(2, min(out_w - x, int(round(width)))); height = max(2, min(out_h - y, int(round(height))))
    width -= width % 2; height -= height % 2
    return x, y, max(2, width), max(2, height)


def boxblur_filter(width: int, height: int, desired_radius: int) -> tuple[str, int, int]:
    luma, chroma = safe_boxblur_radii(width, height, desired_radius)
    value = f"boxblur=luma_radius={luma}:luma_power=2:chroma_radius={chroma}:chroma_power=2"
    return value, luma, chroma


def export_video(
    input_path: str,
    output_path: str,
    options: ExportOptions,
    log=None,
    process_holder=None,
    fast_preview: bool = False,
    log_file=None,
    stage: str = "final render",
):
    ffmpeg = find_binary("ffmpeg")
    info = probe(input_path)
    input_path = info.get("normalized_path", input_path)
    duration = info["duration"]

    cmd = [ffmpeg, "-y", "-i", input_path]
    input_count = 1

    narration_idx = None
    logo_idx = None
    accompaniment_idx = None
    music_idx = None
    canvas_background_idx = None

    if options.narration_path and Path(options.narration_path).exists():
        narration_idx = input_count
        cmd += ["-i", options.narration_path]
        input_count += 1

    if options.logo_path and Path(options.logo_path).exists():
        logo_idx = input_count
        cmd += ["-i", options.logo_path]
        input_count += 1

    if (
        options.source_audio_mode == "Chỉ nhạc nền đã tách"
        and options.accompaniment_path
        and Path(options.accompaniment_path).exists()
    ):
        accompaniment_idx = input_count
        cmd += ["-i", options.accompaniment_path]
        input_count += 1

    if options.background_music_path and Path(options.background_music_path).exists():
        music_idx = input_count
        if options.background_music_loop:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", options.background_music_path]
        input_count += 1

    if options.canvas_background_mode == "image" and options.canvas_background_image and Path(options.canvas_background_image).exists():
        canvas_background_idx = input_count
        cmd += ["-loop", "1", "-i", options.canvas_background_image]
        input_count += 1

    # Basic Editor can add multiple timed image layers.
    editor_layers = [
        dict(x)
        for x in (getattr(options, "editor_layers", []) or [])
        if isinstance(x, dict) and x.get("enabled", True)
    ]
    # Layer timing follows the edited video if global playback speed changes.
    timing_speed = max(0.01, float(getattr(options, "speed", 1.0) or 1.0))
    for layer in editor_layers:
        layer["start"] = max(
            0.0,
            float(layer.get("start", 0.0) or 0.0) / timing_speed,
        )
        layer["end"] = max(
            layer["start"] + 0.01,
            float(layer.get("end", duration) or duration) / timing_speed,
        )
    editor_image_inputs = []
    editor_video_inputs = []
    for layer_index, layer in enumerate(editor_layers):
        if layer.get("type") == "video":
            path = str(layer.get("path", "") or "")
            if path and Path(path).exists():
                video_input_idx = input_count; cmd += ["-stream_loop", "-1", "-i", path]; input_count += 1
                editor_video_inputs.append((layer_index, video_input_idx, layer))
            continue
        if layer.get("type") != "image":
            continue
        path = str(layer.get("path", "") or "")
        if not path or not Path(path).exists():
            continue
        image_input_idx = input_count
        cmd += ["-loop", "1", "-i", path]
        input_count += 1
        editor_image_inputs.append((layer_index, image_input_idx, layer))

    fc: list[str] = []

    # ---------------- Video chain ----------------
    pre = []
    if abs(options.speed - 1.0) > 0.001:
        pre.append(f"setpts=PTS/{options.speed:.6f}")
    if pre:
        fc.append(f"[0:v]{','.join(pre)}[vpre]")
    else:
        fc.append("[0:v]null[vpre]")
    current = "vpre"

    target = parse_resolution(options.resolution)
    out_w = target[0] if target else max(2, info.get("width") or 1920)
    out_h = target[1] if target else max(2, info.get("height") or 1080)
    transform = dict(getattr(options, "video_transform", {}) or {})
    transform.setdefault("fit_mode", options.fit_mode)

    if target:
        w, h = target
        transform_fit = str(transform.get("fit_mode", options.fit_mode)).lower()
        fit_rule = "increase" if transform_fit == "fill" else "decrease"
        sx = max(0.01, float(transform.get("scale_x", 100)) / 100.0); sy = max(0.01, float(transform.get("scale_y", 100)) / 100.0)
        foreground = [f"scale={w}:{h}:force_original_aspect_ratio={fit_rule}", f"scale=trunc(iw*{sx}/2)*2:trunc(ih*{sy}/2)*2"]
        if transform.get("flip_horizontal"): foreground.append("hflip")
        if transform.get("flip_vertical"): foreground.append("vflip")
        rotation = float(transform.get("rotation", 0) or 0)
        if abs(rotation) > 0.001: foreground.append(f"rotate={rotation}*PI/180:ow=rotw(iw):oh=roth(ih):c=none")
        foreground += ["format=rgba", f"colorchannelmixer=aa={max(0.0, min(1.0, float(transform.get('opacity', 100)) / 100.0)):.4f}"]
        fg_chain = ",".join(foreground)
        position_x = float(transform.get("position_x", 50) or 50) / 100.0
        position_y = float(transform.get("position_y", 50) or 50) / 100.0
        overlay_xy = f"x='(W-w)*{position_x:.6f}':y='(H-h)*{position_y:.6f}'"
        background_mode = str(getattr(options, "canvas_background_mode", "none") or "none")
        if background_mode == "blur":
            blur = max(1, min(80, int(getattr(options, "canvas_background_blur", 24))))
            brightness = max(-1.0, min(1.0, float(getattr(options, "canvas_background_brightness", -15)) / 100.0))
            opacity = max(0.0, min(1.0, float(getattr(options, "canvas_background_opacity", 100)) / 100.0))
            fc += [
                f"[{current}]split=2[vbg0][vfg0]",
                f"[vbg0]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur={blur}:3,eq=brightness={brightness:.3f},format=rgba,colorchannelmixer=aa={opacity:.3f}[vbg]",
                f"[vfg0]{fg_chain}[vfg]",
                f"[vbg][vfg]overlay={overlay_xy}[vfit]",
            ]
            current = "vfit"
        elif background_mode == "image" and canvas_background_idx is not None:
            image_fit = str(getattr(options, "canvas_background_image_fit", "cover"))
            if image_fit == "stretch": bg_chain = f"scale={w}:{h}"
            elif image_fit == "contain": bg_chain = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
            else: bg_chain = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
            opacity = max(0.0, min(1.0, float(getattr(options, "canvas_background_opacity", 100)) / 100.0))
            fc += [f"[{canvas_background_idx}:v]{bg_chain},format=rgba,colorchannelmixer=aa={opacity:.3f}[vbg]", f"[{current}]{fg_chain}[vfg]", f"[vbg][vfg]overlay={overlay_xy}[vfit]"]
            current = "vfit"
        else:
            color = str(getattr(options, "canvas_background_color", "#000000") or "#000000").replace("#", "0x")
            fc += [f"color=c={color}:s={w}x{h}:r=30[canvas]", f"[{current}]{fg_chain}[vfg]", f"[canvas][vfg]overlay={overlay_xy}:shortest=1[vfit]"]
            current = "vfit"

    effects = []
    if options.mirror:
        effects.append("hflip")

    if options.zoom > 1.001 and not options.auto_zoom:
        z = min(2.0, max(1.0, options.zoom))
        effects += [
            f"scale=trunc(iw*{z}/2)*2:trunc(ih*{z}/2)*2",
            f"crop=iw/{z}:ih/{z}",
        ]

    if options.auto_zoom:
        zmax = max(1.01, min(1.50, options.auto_zoom_max))
        cycle = max(0.5, min(30.0, options.auto_zoom_cycle))
        # Smooth in/out zoom centered on the subject. 30fps output is predictable across source formats.
        effects.append(
            "zoompan="
            f"z='1+({zmax-1:.5f})*(0.5-0.5*cos(2*PI*on/(30*{cycle:.4f})))':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={out_w}x{out_h}:fps=30"
        )

    if (
        abs(options.brightness) > 0.0001
        or abs(options.contrast - 1.0) > 0.0001
        or abs(options.saturation - 1.0) > 0.0001
    ):
        effects.append(
            f"eq=brightness={max(-1.0,min(1.0,options.brightness)):.3f}:"
            f"contrast={max(0.1,min(3.0,options.contrast)):.3f}:"
            f"saturation={max(0.0,min(3.0,options.saturation)):.3f}"
        )

    if options.sharpen > 0.001:
        amount = max(0.0, min(2.0, options.sharpen))
        effects.append(f"unsharp=5:5:{amount:.3f}:5:5:0")

    if options.vignette:
        effects.append("vignette=PI/5")

    if options.border > 0:
        b = min(100, int(options.border))
        effects.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t={b}")

    if "60FPS" in str(options.resolution).upper():
        effects.append("fps=60")

    if effects:
        fc.append(f"[{current}]{','.join(effects)}[veffects]")
        current = "veffects"

    # Multiple blur/privacy zones.
    zones = [dict(zone) for zone in (getattr(options, "blur_zones", []) or [])
             if isinstance(zone, dict) and zone.get("enabled", True) and zone.get("visible", True)]
    if options.blur_enabled and not zones and options.blur_w > 0 and options.blur_h > 0:
        # Backward compatibility with old pixel-based project.
        zones = [{
            "x_px": max(0, options.blur_x),
            "y_px": max(0, options.blur_y),
            "w_px": max(2, options.blur_w),
            "h_px": max(2, options.blur_h),
        }]

    if options.blur_enabled:
        for zi, z in enumerate(zones):
            style = str(z.get("style") or getattr(options, "blur_style", "Đen mờ"))
            zone_strength = z.get("strength", getattr(options, "blur_opacity", 20))
            try: opacity = max(0, min(100, int(float(zone_strength))))
            except (TypeError, ValueError): opacity = max(0, min(100, int(getattr(options, "blur_opacity", 20))))
            if "x_px" in z:
                raw_x = z["x_px"]; raw_y = z["y_px"]
                raw_w = z["w_px"]; raw_h = z["h_px"]
            else:
                mapped = source_zone_canvas_rect(
                    z, info.get("width") or out_w, info.get("height") or out_h,
                    out_w, out_h, transform,
                )
                raw_x, raw_y, raw_w, raw_h = mapped.x, mapped.y, mapped.width, mapped.height
            x, y, zw, zh = safe_blur_crop_rect(raw_x, raw_y, raw_w, raw_h, out_w, out_h)
            desired_radius = 0 if style == "Đen mờ" else max(0, round(4 + opacity * 0.22))
            blur_filter, luma_radius, chroma_radius = boxblur_filter(zw, zh, desired_radius)
            blur_log = (
                "[BLUR EXPORT]\n"
                f"id={z.get('id', '')}\nsource={z.get('source', 'manual')}\n"
                f"rect={x},{y},{zw},{zh}\ndesired_radius={desired_radius}\n"
                f"luma_radius={luma_radius}\nchroma_radius={chroma_radius}"
            )
            if log: log(blur_log)
            if log_file: append_render_log(log_file, blur_log)

            if style == "Đen mờ":
                alpha = max(0.02, min(1.0, opacity / 100.0))
                fc.append(
                    f"[{current}]drawbox=x={x}:y={y}:w={zw}:h={zh}:"
                    f"color=black@{alpha:.3f}:t=fill[vzone{zi}]"
                )
            else:
                fc += [
                    f"[{current}]split=2[zbase{zi}][zcrop{zi}]",
                    f"[zcrop{zi}]crop={zw}:{zh}:{x}:{y},{blur_filter}[zblur{zi}]",
                    f"[zbase{zi}][zblur{zi}]overlay={x}:{y}[vzone{zi}]",
                ]
            current = f"vzone{zi}"

    if logo_idx is not None:
        scale = min(0.5, max(0.03, options.logo_scale))
        logo_width = max(24, round(out_w * scale))
        opacity = max(0.0, min(1.0, int(getattr(options, "logo_opacity", 100)) / 100.0))
        lx = max(1.0, min(99.0, float(getattr(options, "logo_x_percent", 88.0)))) / 100.0
        ly = max(1.0, min(99.0, float(getattr(options, "logo_y_percent", 10.0)))) / 100.0
        # Keep the expression comma-free; commas inside overlay x/y need escaping
        # and are fragile across FFmpeg builds. UI constrains positions to safe percentages.
        pos = f"W*{lx:.6f}-w/2:H*{ly:.6f}-h/2"

        logo_filters = [f"scale={logo_width}:-1", "format=rgba"]
        if getattr(options, "logo_remove_white_bg", False):
            logo_filters.append("colorkey=0xFFFFFF:0.16:0.08")
        if opacity < 0.999:
            logo_filters.append(f"colorchannelmixer=aa={opacity:.3f}")

        fc += [
            f"[{logo_idx}:v]{','.join(logo_filters)}[logo]",
            f"[{current}][logo]overlay={pos}:format=auto[vlogo]",
        ]
        current = "vlogo"

    # Timed overlay videos. Chroma key is explicit and never presented as AI removal.
    for layer_index, video_input_idx, layer in editor_video_inputs:
        scale_pct = max(2.0, min(100.0, float(layer.get("scale", 35.0) or 35.0)))
        layer_width = max(20, round(out_w * scale_pct / 100.0)); opacity = max(0.01, min(1.0, float(layer.get("opacity", 100)) / 100.0))
        x_pct = float(layer.get("x", 50.0)) / 100.0; y_pct = float(layer.get("y", 50.0)) / 100.0
        start = max(0.0, float(layer.get("start", 0.0))); end = max(start + 0.05, float(layer.get("end", duration)))
        filters = [f"setpts=PTS-STARTPTS+{start:.4f}/TB", f"scale={layer_width}:-1", "format=rgba"]
        if layer.get("background_removal") == "chroma_key":
            key = str(layer.get("key_color", "#00FF00")).replace("#", "0x")
            filters.append(f"colorkey={key}:{max(0.01,min(1.0,float(layer.get('similarity',0.18)))):.3f}:{max(0.0,min(1.0,float(layer.get('blend',0.08)))):.3f}")
        rotation = float(layer.get("rotation", 0) or 0)
        if abs(rotation) > 0.001: filters.append(f"rotate={rotation}*PI/180:ow=rotw(iw):oh=roth(ih):c=none")
        if opacity < 0.999: filters.append(f"colorchannelmixer=aa={opacity:.3f}")
        input_label = f"edvidin{layer_index}"; output_label = f"edvidout{layer_index}"
        fc.append(f"[{video_input_idx}:v]{','.join(filters)}[{input_label}]")
        fc.append(f"[{current}][{input_label}]overlay=W*{x_pct:.6f}-w/2:H*{y_pct:.6f}-h/2:enable='between(t,{start:.4f},{end:.4f})':shortest=0:format=auto[{output_label}]")
        current = output_label

    # Multiple Basic Editor image layers. Their visibility is controlled by
    # each layer's start/end timeline, just like CapCut overlay tracks.
    for layer_index, image_input_idx, layer in editor_image_inputs:
        scale_pct = max(2.0, min(80.0, float(layer.get("scale", 20.0) or 20.0)))
        layer_width = max(20, round(out_w * scale_pct / 100.0))
        opacity = max(0.01, min(1.0, float(layer.get("opacity", 100) or 100) / 100.0))
        x_pct = max(1.0, min(99.0, float(layer.get("x", 50.0) or 50.0))) / 100.0
        y_pct = max(1.0, min(99.0, float(layer.get("y", 50.0) or 50.0))) / 100.0
        start = max(0.0, float(layer.get("start", 0.0) or 0.0))
        end = max(start + 0.05, float(layer.get("end", duration) or duration))
        end = min(duration / max(0.01, options.speed), end)

        input_label = f"edimgin{layer_index}"
        output_label = f"edimgout{layer_index}"
        filters = [
            f"scale={layer_width}:-1",
            "format=rgba",
        ]
        rotation = float(layer.get("rotation", 0) or 0)
        if abs(rotation) > 0.001:
            filters.append(f"rotate={rotation}*PI/180:ow=rotw(iw):oh=roth(ih):c=none")
        if opacity < 0.999:
            filters.append(f"colorchannelmixer=aa={opacity:.3f}")
        fc.append(
            f"[{image_input_idx}:v]{','.join(filters)}[{input_label}]"
        )
        fc.append(
            f"[{current}][{input_label}]"
            f"overlay=W*{x_pct:.6f}-w/2:H*{y_pct:.6f}-h/2:"
            f"enable='between(t,{start:.4f},{end:.4f})':format=auto"
            f"[{output_label}]"
        )
        current = output_label

    temp_ass = None
    editor_text_layers = [
        layer for layer in editor_layers
        if layer.get("type") == "text" and str(layer.get("text", "") or "").strip()
    ]
    should_build_ass = (
        (options.burn_subtitle and options.subtitle_path and Path(options.subtitle_path).exists())
        or bool(options.overlay_text.strip())
        or bool(editor_text_layers)
    )
    if should_build_ass:
        tmp = tempfile.NamedTemporaryFile(suffix='.ass', delete=False)
        temp_ass = tmp.name
        tmp.close()
        ass_path = subtitle_engine.prepare_ass(
            options.subtitle_path if options.burn_subtitle else "",
            temp_ass,
            options.subtitle_style,
            out_w, out_h,
            overlay_text=options.overlay_text,
            overlay_position=options.overlay_position,
            overlay_font_name=getattr(options, "overlay_font_name", "Arial"),
            overlay_font_size=options.overlay_font_size,
            overlay_color=options.overlay_color,
            overlay_x_percent=getattr(options, "overlay_x_percent", 12.0),
            overlay_y_percent=getattr(options, "overlay_y_percent", 8.0),
            duration=(duration / max(0.01, options.speed)),
            extra_text_layers=editor_text_layers,
        )
        sub = _escape_sub_path(ass_path)
        fc.append(f"[{current}]subtitles='{sub}'[vsub]")
        current = "vsub"

    # ---------------- Audio chain ----------------
    audio_sources: list[str] = []
    base_audio_label = None
    mode = options.source_audio_mode

    if mode == "Chỉ nhạc nền đã tách" and accompaniment_idx is not None:
        filters = ["aresample=48000"]
        if abs(options.speed - 1.0) > 0.001:
            filters.append(_atempo_chain(options.speed))
        filters.append(f"volume={_safe_volume(options.source_volume):.3f}")
        fc.append(f"[{accompaniment_idx}:a]{','.join(filters)}[abase]")
        base_audio_label = "abase"
    elif mode != "Tắt toàn bộ âm gốc" and info["has_audio"]:
        filters = ["aresample=48000"]
        if abs(options.speed - 1.0) > 0.001:
            filters.append(_atempo_chain(options.speed))
        filters.append(f"volume={_safe_volume(options.source_volume):.3f}")
        fc.append(f"[0:a]{','.join(filters)}[abase]")
        base_audio_label = "abase"

    narration_label = None
    if narration_idx is not None:
        n_speed = max(0.25, min(4.0, options.narration_speed * options.speed))
        filters = ["aresample=48000"]
        if abs(n_speed - 1.0) > 0.001:
            filters.append(_atempo_chain(n_speed))
        filters.append(f"volume={_safe_volume(options.narration_volume):.3f}")
        fc.append(f"[{narration_idx}:a]{','.join(filters)}[anar]")
        narration_label = "anar"

    music_label = None
    if music_idx is not None:
        fc.append(
            f"[{music_idx}:a]aresample=48000,volume={_safe_volume(options.background_music_volume):.3f}[amusic]"
        )
        music_label = "amusic"

    # Duck original/background automatically while narration is speaking.
    if base_audio_label and narration_label and options.duck_source_under_voice:
        fc.append(
            f"[{base_audio_label}][{narration_label}]"
            "sidechaincompress=threshold=0.025:ratio=8:attack=20:release=350[aducked]"
        )
        base_audio_label = "aducked"

    mix_labels = [x for x in [base_audio_label, narration_label, music_label] if x]
    audio_label = None
    if len(mix_labels) == 1:
        audio_label = mix_labels[0]
    elif len(mix_labels) > 1:
        joined = ''.join(f'[{x}]' for x in mix_labels)
        fc.append(
            f"{joined}amix=inputs={len(mix_labels)}:duration=longest:dropout_transition=2[aout]"
        )
        audio_label = "aout"

    cmd += ["-filter_complex", ";".join(fc), "-map", f"[{current}]"]
    if audio_label:
        cmd += ["-map", f"[{audio_label}]"]

    if fast_preview:
        # Background cache should not steal responsiveness from the editor.
        if nvenc_runtime_available():
            cmd += ["-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll", "-cq", "31"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-threads", "2"]
    else:
        cmd += choose_video_encoder(options.codec, options.encoder)
    if audio_label:
        cmd += ["-c:a", "aac", "-b:a", "192k"]

    if options.strip_metadata:
        cmd += ["-map_metadata", "-1", "-map_chapters", "-1"]

    # We explicitly map our filtered streams; discard source side streams
    # such as MP3 cover-art, embedded subtitles and data.
    cmd += ["-sn", "-dn", "-movflags", "+faststart", "-shortest", output_path]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        if log_file:
            append_render_log(log_file, f"\n[STAGE]\n{stage}")
        run(cmd, log=log, process_holder=process_holder, low_priority=fast_preview, log_file=log_file)
    finally:
        if temp_ass and Path(temp_ass).exists():
            try:
                Path(temp_ass).unlink()
            except Exception:
                pass
    return output_path


def merge_videos(paths: list[str], output_path: str, log=None, process_holder=None):
    if len(paths) < 2:
        raise FFmpegError("Cần ít nhất 2 video để ghép.")
    ffmpeg = find_binary("ffmpeg")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_path = f.name
        for p in paths:
            escaped = Path(p).resolve().as_posix().replace("'", r"'\''")
            f.write(f"file '{escaped}'\n")
    try:
        try:
            run(
                [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_path],
                log=log, process_holder=process_holder,
            )
        except FFmpegError:
            # Fallback: normalize to H.264/AAC. Works for many mixed sources.
            temp_dir = Path(tempfile.mkdtemp(prefix="ms_merge_"))
            normalized = []
            try:
                for i, src in enumerate(paths):
                    dst = temp_dir / f"{i:04d}.mp4"
                    run([
                        ffmpeg, "-y", "-i", src,
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                        "-c:a", "aac", "-ar", "48000",
                        str(dst),
                    ], log=log, process_holder=process_holder)
                    normalized.append(str(dst))
                with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f2:
                    list2 = f2.name
                    for p in normalized:
                        f2.write(f"file '{Path(p).resolve().as_posix()}'\n")
                try:
                    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list2, "-c", "copy", output_path],
                        log=log, process_holder=process_holder)
                finally:
                    Path(list2).unlink(missing_ok=True)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
    finally:
        Path(list_path).unlink(missing_ok=True)
    return output_path



def build_scene_timeline_audio(
    scene_chunks: list[dict],
    output_path: str,
    total_duration: float,
) -> list[dict]:
    """Create narration placed at each scene start.

    Unlike the old 30-second chunk concatenation, every AI scene has its own TTS
    file. If a voice line is longer than its scene window it is accelerated just
    enough to fit. If it is shorter, it remains natural and the remaining scene
    time is silence.

    Returned manifest contains the REAL post-fit start/end timestamps. Subtitle
    cues should be generated from this manifest, so captions never outlive the
    voice line.
    """
    if not scene_chunks:
        raise FFmpegError("Chưa có voice scene.")

    ffmpeg = find_binary("ffmpeg")
    total_duration = max(0.2, float(total_duration or 0.0))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Input 0 is a silent bed covering the entire video, ensuring the narration
    # file has exactly the video length even when voice lines have gaps.
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-t", f"{total_duration:.3f}",
        "-i", "anullsrc=r=48000:cl=stereo",
    ]
    for chunk in scene_chunks:
        cmd += ["-i", chunk["path"]]

    filters = ["[0:a]asetpts=PTS-STARTPTS[abase]"]
    labels = ["[abase]"]
    manifest = []

    for i, chunk in enumerate(scene_chunks, start=1):
        source = str(chunk["path"])
        start = max(0.0, float(chunk.get("start", 0.0)))
        scene_end = max(start + 0.1, float(chunk.get("scene_end", start + 0.1)))
        available = max(0.10, scene_end - start)

        actual = _audio_duration(source)
        if actual <= 0:
            raise FFmpegError(f"Không đọc được thời lượng voice: {source}")

        # Voice must never run into the next scene. Only accelerate when needed.
        factor = max(1.0, actual / available)
        factor = min(16.0, factor)
        adjusted = actual / factor
        # Floating-point safety: never let cue pass its scene window.
        adjusted = min(adjusted, available)
        end = min(total_duration, start + adjusted)

        chain = [
            "aresample=48000",
            "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo",
        ]
        if abs(factor - 1.0) > 0.003:
            chain.append(_atempo_chain(factor))
        chain += [
            f"atrim=duration={max(0.05, adjusted):.4f}",
            "asetpts=PTS-STARTPTS",
            f"adelay={round(start * 1000)}:all=1",
        ]

        label = f"seg{i}"
        filters.append(f"[{i}:a]{','.join(chain)}[{label}]")
        labels.append(f"[{label}]")

        # Detect real pauses in the generated voice source. Subtitle timing
        # uses these speech islands so text disappears during audible silence.
        try:
            source_speech = detect_speech_intervals(source)
        except Exception:
            source_speech = [(0.0, actual)]

        timeline_speech = []
        for speech_start, speech_end in source_speech:
            mapped_start = start + max(0.0, speech_start) / factor
            mapped_end = start + max(0.0, speech_end) / factor
            mapped_start = max(start, min(end, mapped_start))
            mapped_end = max(mapped_start, min(end, mapped_end))
            if mapped_end - mapped_start >= 0.08:
                timeline_speech.append([
                    round(mapped_start, 4),
                    round(mapped_end, 4),
                ])

        manifest.append({
            "scene_index": int(chunk.get("scene_index", i - 1)),
            "start": round(start, 4),
            "end": round(end, 4),
            "duration": round(max(0.0, end - start), 4),
            "source_duration": round(actual, 4),
            "speed_factor": round(factor, 4),
            "speech_intervals": timeline_speech,
            "path": source,
            "en_text": str(chunk.get("en_text", "") or ""),
            "vi_text": str(chunk.get("vi_text", "") or ""),
        })

    joined = "".join(labels)
    filters.append(
        f"{joined}amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[aout]"
    )

    run([
        *cmd,
        "-filter_complex", ";".join(filters),
        "-map", "[aout]",
        "-t", f"{total_duration:.3f}",
        "-c:a", "aac", "-b:a", "160k",
        output_path,
    ])
    return manifest



def detect_speech_intervals(
    audio_path: str,
    *,
    silence_db: float = -38.0,
    min_silence: float = 0.22,
) -> list[tuple[float, float]]:
    """Return audible/speech intervals by removing real silent pauses.

    Uses FFmpeg silencedetect. It is intentionally conservative: only pauses
    >= min_silence are removed, so natural micro-pauses do not flicker captions.
    """
    duration = _audio_duration(audio_path)
    if duration <= 0:
        return []

    ffmpeg = find_binary("ffmpeg")
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-i", audio_path,
        "-af", f"silencedetect=noise={float(silence_db):.1f}dB:d={float(min_silence):.3f}",
        "-f", "null",
        "-",
    ]

    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_flags(),
    )
    output = p.stdout or ""

    silence_starts = []
    silence_ends = []
    for line in output.splitlines():
        m = re.search(r"silence_start:\s*([0-9.]+)", line)
        if m:
            silence_starts.append(float(m.group(1)))
        m = re.search(r"silence_end:\s*([0-9.]+)", line)
        if m:
            silence_ends.append(float(m.group(1)))

    silences = []
    open_start = None
    events = []
    for line in output.splitlines():
        ms = re.search(r"silence_start:\s*([0-9.]+)", line)
        if ms:
            open_start = float(ms.group(1))
        me = re.search(r"silence_end:\s*([0-9.]+)", line)
        if me:
            end = float(me.group(1))
            start = 0.0 if open_start is None else open_start
            events.append((max(0.0, start), min(duration, end)))
            open_start = None

    if open_start is not None:
        events.append((max(0.0, open_start), duration))

    # Merge overlapping silence ranges.
    for start, end in sorted(events):
        if end <= start:
            continue
        if silences and start <= silences[-1][1] + 0.01:
            silences[-1] = (silences[-1][0], max(silences[-1][1], end))
        else:
            silences.append((start, end))

    if not silences:
        return [(0.0, duration)]

    speech = []
    cursor = 0.0
    for s, e in silences:
        if s - cursor >= 0.08:
            speech.append((cursor, s))
        cursor = max(cursor, e)
    if duration - cursor >= 0.08:
        speech.append((cursor, duration))

    # Very tiny residual islands cause subtitle flicker; ignore them.
    speech = [
        (round(s, 4), round(e, 4))
        for s, e in speech
        if e - s >= 0.10
    ]
    return speech or [(0.0, duration)]


def _split_text_across_intervals(
    text: str,
    intervals: list[tuple[float, float]],
) -> list[tuple[float, float, str]]:
    """Distribute words across real speech islands while preserving silence gaps."""
    words = str(text or "").strip().split()
    usable = [
        (float(s), float(e))
        for s, e in intervals
        if float(e) - float(s) >= 0.10
    ]
    if not words or not usable:
        return []

    # More speech islands than words: keep the longest N intervals in time order.
    if len(usable) > len(words):
        ranked = sorted(
            enumerate(usable),
            key=lambda x: x[1][1] - x[1][0],
            reverse=True,
        )[:len(words)]
        keep = {i for i, _ in ranked}
        usable = [iv for i, iv in enumerate(usable) if i in keep]

    durations = [max(0.01, e - s) for s, e in usable]
    total = sum(durations) or 1.0

    result = []
    consumed = 0
    cumulative = 0.0
    n_words = len(words)
    n_intervals = len(usable)

    for i, ((start, end), dur) in enumerate(zip(usable, durations)):
        if i == n_intervals - 1:
            stop = n_words
        else:
            cumulative += dur
            target = round(n_words * cumulative / total)
            minimum_stop = consumed + 1
            maximum_stop = n_words - (n_intervals - i - 1)
            stop = max(minimum_stop, min(maximum_stop, target))

        piece = " ".join(words[consumed:stop]).strip()
        if piece:
            result.append((start, end, piece))
        consumed = stop

    return result


def _word_weights(words: list[str]) -> list[float]:
    """Approximate natural TTS word duration without another AI request."""
    result = []
    for word in words:
        clean = re.sub(r"[^\w']", "", str(word), flags=re.UNICODE)
        letters = max(1, len(clean))
        weight = 0.72 + min(2.1, math.sqrt(letters) * 0.38)
        if re.search(r"[,;:]$", str(word)):
            weight += 0.20
        if re.search(r"[.!?]$", str(word)):
            weight += 0.34
        result.append(weight)
    return result


def split_text_to_word_cues(
    text: str,
    intervals: list[tuple[float, float]],
    *,
    min_word_duration: float = 0.065,
) -> list[tuple[float, float, str]]:
    """One cue per word, distributed inside REAL audible speech intervals.

    Silence gaps are preserved because the input intervals come from
    silencedetect. Longer words receive slightly more time than short words.
    """
    words = str(text or "").strip().split()
    intervals = [
        (float(s), float(e))
        for s, e in intervals
        if float(e) - float(s) >= 0.055
    ]
    if not words or not intervals:
        return []

    # If there are more audible islands than words, keep the longest islands.
    if len(intervals) > len(words):
        keep = sorted(
            sorted(
                range(len(intervals)),
                key=lambda i: intervals[i][1] - intervals[i][0],
                reverse=True,
            )[:len(words)]
        )
        intervals = [intervals[i] for i in keep]

    durations = [max(0.01, e - s) for s, e in intervals]
    total_duration = sum(durations) or 1.0

    # Allocate number of words to each audible island by duration.
    allocations = []
    remaining = len(words)
    assigned = 0
    cumulative = 0.0
    for i, dur in enumerate(durations):
        islands_left = len(durations) - i - 1
        if i == len(durations) - 1:
            count = remaining
        else:
            cumulative += dur
            target_total = round(len(words) * cumulative / total_duration)
            count = max(1, target_total - assigned)
            count = min(count, remaining - islands_left)
        allocations.append(count)
        assigned += count
        remaining -= count

    cues = []
    word_pos = 0

    for (start, end), count in zip(intervals, allocations):
        segment_words = words[word_pos:word_pos + count]
        word_pos += count
        if not segment_words:
            continue

        weights = _word_weights(segment_words)
        weights_sum = sum(weights) or 1.0
        segment_duration = max(0.01, end - start)
        cursor = start

        # Weighted boundaries that still exactly finish at the speech island end.
        cumulative_weight = 0.0
        for j, (word, weight) in enumerate(zip(segment_words, weights)):
            cumulative_weight += weight
            if j == len(segment_words) - 1:
                word_end = end
            else:
                word_end = start + segment_duration * cumulative_weight / weights_sum

                # Keep a minimum visible time for the current and remaining words.
                remaining_count = len(segment_words) - j - 1
                min_end = cursor + min_word_duration
                max_end = end - remaining_count * min_word_duration
                if max_end < min_end:
                    # Very fast speech: permit shorter cues but never zero.
                    word_end = max(cursor + 0.035, min(end, word_end))
                else:
                    word_end = max(min_end, min(max_end, word_end))

            word_end = max(cursor + 0.030, min(end, word_end))
            cues.append((
                round(cursor, 4),
                round(word_end, 4),
                str(word),
            ))
            cursor = word_end

    return cues

def write_srt_from_voice_manifest(
    manifest: list[dict],
    output_path: str,
    language: str = "en",
    max_chars: int = 32,
    single_line: bool = True,
    hide_on_voice_pause: bool = True,
    pause_ms: int = 220,
    word_by_word: bool = False,
) -> str:
    """Create subtitles from REAL generated voice durations.

    In single-line mode, a long TTS sentence is split into several short cue
    phrases INSIDE the exact same voice interval. Therefore subtitles never
    become longer than the narration and never wrap to a second visual line.
    """
    key = "vi_text" if str(language).lower().startswith("vi") else "en_text"
    cues = []

    for item in manifest:
        text = str(item.get(key, "") or "").strip()
        if not text:
            continue

        start = float(item.get("start", 0.0))
        end = float(item.get("end", start + 0.1))
        if end <= start:
            continue

        speech_intervals = []
        if hide_on_voice_pause:
            for pair in item.get("speech_intervals", []) or []:
                try:
                    s, e = float(pair[0]), float(pair[1])
                except Exception:
                    continue
                s = max(start, min(end, s))
                e = max(s, min(end, e))
                if e - s >= 0.08:
                    speech_intervals.append((s, e))

            # Backward compatibility: old v1.0.9 manifests do not yet contain
            # speech_intervals. Detect them now from each original TTS chunk.
            if not speech_intervals:
                source = str(item.get("path", "") or "")
                if source and Path(source).exists():
                    try:
                        source_intervals = detect_speech_intervals(
                            source,
                            min_silence=max(
                                0.12,
                                min(1.2, int(pause_ms) / 1000.0),
                            ),
                        )
                        factor = max(
                            0.01,
                            float(item.get("speed_factor", 1.0) or 1.0),
                        )
                        for ss, se in source_intervals:
                            s = start + ss / factor
                            e = start + se / factor
                            s = max(start, min(end, s))
                            e = max(s, min(end, e))
                            if e - s >= 0.08:
                                speech_intervals.append((s, e))
                    except Exception:
                        speech_intervals = []

        if speech_intervals:
            if word_by_word:
                speech_cues = split_text_to_word_cues(
                    text,
                    speech_intervals,
                )
            else:
                # Create actual empty gaps wherever voice analysis found silence.
                speech_cues = _split_text_across_intervals(
                    text,
                    speech_intervals,
                )
            cues.extend(speech_cues)
        else:
            if word_by_word:
                cues.extend(
                    split_text_to_word_cues(
                        text,
                        [(start, end)],
                    )
                )
            else:
                cues.append((start, end, text))

    # Word Pop Sync already has one word per cue; never combine it back into phrases.
    if single_line and not word_by_word:
        cues = subtitle_engine.split_single_line_cues(
            cues,
            max_chars=max_chars,
            uppercase=False,
        )

    return subtitle_engine.write_srt_cues(cues, output_path)


def load_voice_manifest(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def build_timeline_audio(chunks: list[dict], output_path: str, fit_percent: int = 70):
    """Build one narration timeline.

    fit_percent controls how strongly each TTS chunk is time-stretched toward its
    target scene duration. 0 = natural voice then pad/trim, 100 = fit duration as
    closely as possible before final pad/trim.
    """
    ffmpeg = find_binary("ffmpeg")
    if not chunks:
        raise FFmpegError("Chưa có voice chunk.")

    cmd = [ffmpeg, "-y"]
    for c in chunks:
        cmd += ["-i", c["path"]]

    filters = []
    labels = []
    strength = max(0.0, min(1.0, int(fit_percent) / 100.0))

    for i, c in enumerate(chunks):
        target = max(0.1, float(c["duration"]))
        actual = _audio_duration(c["path"]) or target
        perfect_factor = actual / target
        factor = 1.0 + (perfect_factor - 1.0) * strength
        factor = max(0.25, min(4.0, factor))

        label = f"a{i}"
        chain = ["aresample=24000"]
        if abs(factor - 1.0) > 0.005:
            chain.append(_atempo_chain(factor))
        chain += [
            f"apad=pad_dur={target:.3f}",
            f"atrim=duration={target:.3f}",
            "asetpts=PTS-STARTPTS",
        ]
        filters.append(f"[{i}:a]{','.join(chain)}[{label}]")
        labels.append(f"[{label}]")

    filters.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]")
    run([
        *cmd,
        "-filter_complex", ";".join(filters),
        "-map", "[out]", "-c:a", "aac", "-b:a", "160k",
        output_path,
    ])
    return output_path
