from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import os


class VocalSeparationError(RuntimeError):
    pass


def separate_vocals(input_path: str, out_dir: str, log=None, process_holder=None) -> dict:
    """Use optional Demucs to produce vocals + no_vocals stems.

    Demucs is deliberately optional because installing Torch can be large.
    Run install_demucs.bat once if this feature is needed.
    """
    src = Path(input_path)
    if not src.exists() or not src.is_file():
        raise VocalSeparationError(f"Không tìm thấy file:\n{src}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, '-m', 'demucs',
        '--two-stems=vocals',
        '-o', str(out),
        str(src),
    ]
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    if log:
        log(' '.join(cmd))
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace', creationflags=flags,
    )
    if process_holder is not None:
        process_holder['process'] = p
    lines = []
    assert p.stdout is not None
    for line in p.stdout:
        lines.append(line)
        if log:
            log(line.rstrip())
    rc = p.wait()
    if process_holder is not None:
        process_holder['process'] = None
    if rc != 0:
        joined = '\n'.join(lines[-40:])
        if 'No module named demucs' in joined or 'demucs' in joined.lower() and 'module' in joined.lower():
            raise VocalSeparationError(
                'Chưa cài Demucs. Hãy chạy install_demucs.bat rồi mở lại app.\n\n' + joined
            )
        raise VocalSeparationError(joined or f'Demucs exit code {rc}')

    no_vocals = next(out.rglob('no_vocals.wav'), None)
    vocals = next(out.rglob('vocals.wav'), None)
    if not no_vocals:
        raise VocalSeparationError('Demucs chạy xong nhưng không tìm thấy no_vocals.wav.')
    return {
        'accompaniment': str(no_vocals),
        'vocals': str(vocals) if vocals else '',
    }
