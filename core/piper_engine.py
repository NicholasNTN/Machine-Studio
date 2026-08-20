from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen
import json
import os
import re
import subprocess
import sys
import wave


class PiperError(RuntimeError):
    pass


VOICES_JSON_URL = (
    "https://huggingface.co/rhasspy/piper-voices/"
    "resolve/main/voices.json?download=true"
)

# Known valid/common voices; online catalog expands this to the full list.
FEATURED_VOICES = [
    "en_US-lessac-medium",
    "en_US-lessac-high",
    "en_US-lessac-low",
    "en_US-amy-medium",
    "en_US-amy-low",
    "en_US-bryce-medium",
    "en_US-john-medium",
    "en_US-norman-medium",
    "en_US-ryan-medium",
]

LANGUAGE_NAMES = {
    "en_US": "English US",
    "en_GB": "English UK",
    "vi_VN": "Tiếng Việt",
    "zh_CN": "中文",
    "de_DE": "Deutsch",
    "fr_FR": "Français",
    "es_ES": "Español",
    "it_IT": "Italiano",
    "pt_BR": "Português BR",
    "pt_PT": "Português PT",
    "pl_PL": "Polski",
    "ru_RU": "Русский",
    "ja_JP": "日本語",
}


_VOICE_CACHE = {
    "voice_id": None,
    "model_path": None,
    "voice": None,
}


def piper_installed() -> bool:
    try:
        import piper  # noqa: F401
        return True
    except Exception:
        return False


def voices_dir(root: str | Path) -> Path:
    path = Path(root) / "piper_voices"
    path.mkdir(parents=True, exist_ok=True)
    return path


def catalog_cache_path(root: str | Path) -> Path:
    return voices_dir(root) / "voices_catalog.json"


def voice_paths(root: str | Path, voice_id: str) -> tuple[Path, Path]:
    folder = voices_dir(root)
    model = folder / f"{voice_id}.onnx"
    config = folder / f"{voice_id}.onnx.json"
    return model, config


def is_voice_installed(root: str | Path, voice_id: str) -> bool:
    model, config = voice_paths(root, voice_id)
    return (
        model.exists()
        and model.stat().st_size > 0
        and config.exists()
        and config.stat().st_size > 0
    )


def installed_voices(root: str | Path) -> list[str]:
    folder = voices_dir(root)
    result = []
    for model in sorted(folder.glob("*.onnx")):
        voice_id = model.stem
        if is_voice_installed(root, voice_id):
            result.append(voice_id)
    return result


def _fallback_catalog() -> dict:
    data = {}
    for voice_id in FEATURED_VOICES:
        meta = parse_voice_id(voice_id)
        data[voice_id] = {
            "key": voice_id,
            "name": meta["name"],
            "language": meta["language"],
            "quality": meta["quality"],
            "num_speakers": 1,
            "files": {},
        }
    return data


def fetch_catalog(root: str | Path, timeout: int = 25) -> dict:
    """Fetch official Piper voices.json and cache it locally."""
    try:
        with urlopen(VOICES_JSON_URL, timeout=timeout) as response:
            data = json.load(response)
        if not isinstance(data, dict) or not data:
            raise PiperError("voices.json không hợp lệ.")

        cache = catalog_cache_path(root)
        cache.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return data
    except Exception as e:
        cached = load_cached_catalog(root)
        if cached:
            return cached
        raise PiperError(
            "Không tải được catalog Piper. Kiểm tra Internet rồi thử lại.\n"
            f"{e}"
        ) from e


def load_cached_catalog(root: str | Path) -> dict:
    cache = catalog_cache_path(root)
    if not cache.exists():
        return {}
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_catalog(root: str | Path, online: bool = False) -> dict:
    if online:
        return fetch_catalog(root)

    cached = load_cached_catalog(root)
    if cached:
        return cached

    fallback = _fallback_catalog()
    for voice_id in installed_voices(root):
        if voice_id not in fallback:
            meta = parse_voice_id(voice_id)
            fallback[voice_id] = {
                "key": voice_id,
                "name": meta["name"],
                "language": meta["language"],
                "quality": meta["quality"],
                "files": {},
            }
    return fallback


def parse_voice_id(voice_id: str) -> dict:
    # <language>-<name>-<quality>, language usually xx_YY
    match = re.match(
        r"^(?P<language>[^-]+)-(?P<name>[^-]+)-(?P<quality>.+)$",
        voice_id or "",
    )
    if not match:
        return {
            "language": "",
            "name": voice_id or "",
            "quality": "",
        }
    return match.groupdict()


def voice_label(voice_id: str, info: dict | None = None) -> str:
    info = info or {}
    parsed = parse_voice_id(voice_id)
    language = (
        info.get("language")
        or parsed.get("language")
        or ""
    )
    name = info.get("name") or parsed.get("name") or voice_id
    quality = (
        info.get("quality")
        or parsed.get("quality")
        or ""
    )
    language_label = LANGUAGE_NAMES.get(language, language)
    quality_label = quality.capitalize() if quality else ""
    return (
        f"{language_label} — {str(name).replace('_', ' ').title()}"
        + (f" ({quality_label})" if quality_label else "")
    )


def voice_size_bytes(info: dict | None) -> int:
    if not isinstance(info, dict):
        return 0
    total = 0
    for file_info in (info.get("files") or {}).values():
        if isinstance(file_info, dict):
            try:
                total += int(file_info.get("size_bytes", 0) or 0)
            except Exception:
                pass
    return total


def human_size(size: int) -> str:
    size = int(size or 0)
    if size <= 0:
        return ""
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return ""


def model_card_url(voice_id: str) -> str:
    parsed = parse_voice_id(voice_id)
    language = parsed["language"]
    name = parsed["name"]
    quality = parsed["quality"]
    family = language.split("_", 1)[0] if "_" in language else language
    return (
        "https://huggingface.co/rhasspy/piper-voices/blob/main/"
        f"{family}/{language}/{name}/{quality}/MODEL_CARD"
    )


def download_voice(
    root: str | Path,
    voice_id: str,
    *,
    log=None,
    force: bool = False,
) -> str:
    """Download only the selected voice model + config."""
    if not piper_installed():
        raise PiperError(
            "Chưa cài Piper TTS. Hãy chạy lại install.bat "
            "hoặc install_piper.bat."
        )

    folder = voices_dir(root)
    if is_voice_installed(root, voice_id) and not force:
        if log:
            log(f"[PIPER] Voice đã có offline: {voice_id}")
        return voice_id

    cmd = [
        sys.executable,
        "-m",
        "piper.download_voices",
        "--download-dir",
        str(folder),
    ]
    if force:
        cmd.append("--force-redownload")
    cmd.append(voice_id)

    if log:
        log(f"[PIPER] Tải voice: {voice_id}")
        log(f"[PIPER] Folder: {folder}")

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )

    lines = []
    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.rstrip()
        lines.append(line)
        if log:
            log("[PIPER] " + line)

    code = process.wait()
    if code != 0:
        raise PiperError(
            "Tải Piper voice thất bại:\n"
            + "\n".join(lines[-30:])
        )

    if not is_voice_installed(root, voice_id):
        raise PiperError(
            "Piper báo tải xong nhưng không tìm thấy đủ .onnx + .onnx.json."
        )

    if log:
        model, _ = voice_paths(root, voice_id)
        log(
            f"[PIPER] Đã tải offline: {voice_id} "
            f"({human_size(model.stat().st_size)})"
        )
    return voice_id


def delete_voice(root: str | Path, voice_id: str) -> None:
    clear_cache(voice_id)
    model, config = voice_paths(root, voice_id)
    for path in (model, config):
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            raise PiperError(f"Không xóa được {path.name}: {e}") from e


def clear_cache(voice_id: str | None = None) -> None:
    if (
        voice_id is None
        or _VOICE_CACHE.get("voice_id") == voice_id
    ):
        _VOICE_CACHE["voice_id"] = None
        _VOICE_CACHE["model_path"] = None
        _VOICE_CACHE["voice"] = None


def _load_voice(root: str | Path, voice_id: str):
    if not piper_installed():
        raise PiperError(
            "Chưa cài piper-tts. Hãy chạy install_piper.bat."
        )

    model, config = voice_paths(root, voice_id)
    if not is_voice_installed(root, voice_id):
        raise PiperError(
            f"Voice '{voice_id}' chưa được tải offline."
        )

    if (
        _VOICE_CACHE.get("voice_id") == voice_id
        and _VOICE_CACHE.get("model_path") == str(model)
        and _VOICE_CACHE.get("voice") is not None
    ):
        return _VOICE_CACHE["voice"]

    try:
        from piper import PiperVoice
        voice = PiperVoice.load(
            str(model),
            config_path=str(config),
            use_cuda=False,
            download_dir=str(voices_dir(root)),
        )
    except Exception as e:
        raise PiperError(
            f"Không load được Piper voice {voice_id}: {e}"
        ) from e

    _VOICE_CACHE["voice_id"] = voice_id
    _VOICE_CACHE["model_path"] = str(model)
    _VOICE_CACHE["voice"] = voice
    return voice


def synthesize(
    root: str | Path,
    voice_id: str,
    text: str,
    out_path: str,
    *,
    speed: float = 1.0,
    log=None,
) -> str:
    if not (text or "").strip():
        raise PiperError("Nội dung TTS đang trống.")

    if not is_voice_installed(root, voice_id):
        download_voice(root, voice_id, log=log)

    voice = _load_voice(root, voice_id)

    try:
        from piper import SynthesisConfig
    except Exception as e:
        raise PiperError(
            "Piper API không đúng phiên bản. Hãy chạy install_piper.bat."
        ) from e

    speed = max(0.5, min(2.0, float(speed)))
    # Piper length_scale > 1 = slower, so invert user speed.
    syn_config = SynthesisConfig(
        length_scale=1.0 / speed,
    )

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with wave.open(str(target), "wb") as wav_file:
            voice.synthesize_wav(
                text,
                wav_file,
                syn_config=syn_config,
            )
    except Exception as e:
        raise PiperError(
            f"Piper synthesize thất bại ({voice_id}): {e}"
        ) from e

    if not target.exists() or target.stat().st_size < 1000:
        raise PiperError(
            "Piper không tạo được file WAV hợp lệ."
        )

    if log:
        log(
            f"[PIPER] Tạo voice xong: {voice_id} -> {target.name}"
        )
    return str(target)
