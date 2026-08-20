from __future__ import annotations

from pathlib import Path
import json


class PresetStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def names(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob('*.json'))

    def save(self, name: str, data: dict):
        safe = ''.join(c for c in name.strip() if c.isalnum() or c in ' _-.').strip() or 'Preset'
        (self.root / f'{safe}.json').write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        return safe

    def load(self, name: str) -> dict:
        return json.loads((self.root / f'{name}.json').read_text(encoding='utf-8'))

    def delete(self, name: str):
        (self.root / f'{name}.json').unlink(missing_ok=True)
