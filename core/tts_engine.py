from __future__ import annotations

from pathlib import Path
import asyncio
import os
import subprocess
import tempfile

from . import gemini_engine as gem
from . import piper_engine


class TTSError(RuntimeError):
    pass


EDGE_FALLBACK_VOICE_EN = "en-US-JennyNeural"


def is_gemini_quota_error(exc: Exception) -> bool:
    """Detect Gemini TTS quota/rate/capacity failures that are safe to fallback."""
    text = str(exc or "").lower()
    return any(
        marker in text
        for marker in (
            "429",
            "quota",
            "rate limit",
            "rate_limit",
            "resource_exhausted",
            "too many requests",
        )
    )


def edge_voice_for_fallback(requested_voice: str = "") -> str:
    voice = (requested_voice or "").strip()
    # Gemini voice names are not Edge voice IDs.
    if voice.lower().endswith("neural"):
        return voice
    return EDGE_FALLBACK_VOICE_EN


def _edge_rate(speed: float) -> str:
    speed = max(0.5, min(2.0, float(speed)))
    pct = round((speed - 1.0) * 100)
    return f'{pct:+d}%'


def generate_edge(text: str, voice: str, out_path: str, speed: float = 1.0) -> str:
    try:
        import edge_tts
    except Exception as e:
        raise TTSError('Chưa cài edge-tts. Hãy chạy lại install.bat.') from e

    async def _run():
        c = edge_tts.Communicate(text=text, voice=voice, rate=_edge_rate(speed))
        await c.save(out_path)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_run())
    return out_path


def generate_sapi(text: str, voice: str, out_path: str, speed: float = 1.0) -> str:
    if os.name != 'nt':
        raise TTSError('Windows SAPI chỉ dùng được trên Windows.')
    # System.Speech Rate accepts -10..10.
    rate = max(-10, min(10, round((speed - 1.0) * 10)))
    esc_text = text.replace("'", "''")
    esc_path = str(Path(out_path).resolve()).replace("'", "''")
    esc_voice = (voice or '').replace("'", "''")
    script = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ('{esc_voice}' -ne '') {{ try {{ $s.SelectVoice('{esc_voice}') }} catch {{ }} }}
$s.Rate = {rate}
$s.SetOutputToWaveFile('{esc_path}')
$s.Speak('{esc_text}')
$s.Dispose()
"""
    flags = subprocess.CREATE_NO_WINDOW
    p = subprocess.run(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', errors='replace', creationflags=flags,
    )
    if p.returncode != 0 or not Path(out_path).exists():
        raise TTSError(p.stderr or p.stdout or 'Windows SAPI tạo voice thất bại.')
    return out_path


def generate_tts(
    engine: str,
    text: str,
    out_path: str,
    speed: float = 1.0,
    voice: str = '',
    api_key: str = '',
    gemini_model: str = '',
    direction: str = '',
    piper_root: str = '',
    log=None,
) -> str:
    engine = (engine or '').lower()
    if 'piper' in engine:
        if not piper_root:
            raise TTSError("Thiếu Piper data root.")
        try:
            return piper_engine.synthesize(
                piper_root,
                voice or "en_US-lessac-medium",
                text,
                out_path,
                speed=speed,
                log=log,
            )
        except piper_engine.PiperError as e:
            raise TTSError(str(e)) from e

    if 'edge' in engine:
        return generate_edge(text, voice or 'en-US-JennyNeural', out_path, speed)
    if 'sapi' in engine or 'windows' in engine:
        return generate_sapi(text, voice, out_path, speed)
    # Gemini output is WAV already. Speed is expressed in direction; final timeline fit handles exact sync.
    d = (direction or '').strip()
    if abs(speed - 1.0) > 0.01:
        d += f' Target speaking speed approximately {speed:.2f}x normal.'
    return gem.tts(api_key, gemini_model, voice or 'Kore', text, out_path, d)
