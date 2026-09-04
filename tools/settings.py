import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "enabled_personas": ["albert", "albertine", "alex"],
    "interaction_mode": "vad",  # "vad" (freihaendig) oder "push_to_talk" (Leertaste)
    "show_debug_info": False,  # z.B. Audio-Chunk-Zaehler im Gespraech
}


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    settings = {**DEFAULT_SETTINGS, **data}
    if not settings.get("enabled_personas"):
        settings["enabled_personas"] = list(DEFAULT_SETTINGS["enabled_personas"])
    return settings


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
