from __future__ import annotations

import os
import platform
import subprocess

try:
    import psutil
except Exception:
    psutil = None


def get_system_summary() -> str:
    parts = []
    cpu = platform.processor() or platform.machine() or "Unknown CPU"
    parts.append(f"CPU: {cpu}")

    if psutil:
        try:
            mem = psutil.virtual_memory()
            total = mem.total / (1024**3)
            free = mem.available / (1024**3)
            parts.append(f"RAM: {total:.1f} GB (trống {free:.1f} GB)")
        except Exception:
            pass

    gpu = detect_gpu()
    if gpu:
        parts.append(f"GPU: {gpu}")
    return " | ".join(parts)


def detect_gpu() -> str:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=4, creationflags=flags,
        )
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return ""
