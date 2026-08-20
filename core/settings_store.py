from __future__ import annotations

from pathlib import Path
import json
import keyring

SERVICE = "MachineScope_Studio"
GEMINI_USER = "gemini_api_key"
PROVIDER_USERS = {
    "Google Gemini": "ai_google_gemini_api_key",
    "CKEY": "ai_ckey_api_key",
    "OpenAI": "ai_openai_api_key",
    "DeepSeek": "ai_deepseek_api_key",
}


class SettingsStore:
    def __init__(self, root: Path):
        self.path = root / "settings.json"
        self.data = {
            "ai_provider": "CKEY",
            "model": "levuphong2909/gemini-3.7-flash-high",
            "ai_base_url": "https://api.xah.io/v1",
            "provider_models": {
                "Google Gemini": "gemini-3.7-flash",
                "CKEY": "levuphong2909/gemini-3.7-flash-high",
                "OpenAI": "gpt-4.1-mini",
                "DeepSeek": "deepseek-chat",
            },
            "provider_base_urls": {
                "Google Gemini": "",
                "CKEY": "https://api.xah.io/v1",
                "OpenAI": "https://api.openai.com/v1",
                "DeepSeek": "https://api.deepseek.com/v1",
            },
            "tts_model": "gemini-3.1-flash-tts-preview",
            "voice": "Kore",
            "output_dir": str(root / "exports"),
            "download_dir": str(root / "downloads"),
            "capcut_path": "",
            "cookies_browser": "",
            "voice_style": (
                "Natural American documentary narrator, confident and curious, "
                "medium pace, clear articulation, slightly energetic."
            ),
        }
        self.load()

    def load(self):
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    self.data.update(saved)
            except Exception:
                pass

    def save(self):
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_api_key(self) -> str:
        try:
            return keyring.get_password(SERVICE, GEMINI_USER) or ""
        except Exception:
            return ""

    def set_api_key(self, value: str):
        value = (value or "").strip()
        if not value:
            return
        keyring.set_password(SERVICE, GEMINI_USER, value)


    def get_provider_api_key(self, provider: str) -> str:
        provider = (provider or "").strip()
        username = PROVIDER_USERS.get(provider)
        if not username:
            return ""
        try:
            value = keyring.get_password(SERVICE, username) or ""
        except Exception:
            value = ""
        if provider == "Google Gemini" and not value:
            value = self.get_api_key()
        return value

    def set_provider_api_key(self, provider: str, value: str):
        provider = (provider or "").strip()
        username = PROVIDER_USERS.get(provider)
        value = (value or "").strip()
        if not username or not value:
            return
        keyring.set_password(SERVICE, username, value)
