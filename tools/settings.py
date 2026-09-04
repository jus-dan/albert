import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "settings.json"

# Von der Realtime API (gpt-realtime) unterstuetzte Stimmen. "cedar" und
# "marin" sind laut OpenAI-Doku die neuesten/natuerlichsten.
VALID_VOICES = [
    "alloy", "ash", "ballad", "cedar", "coral",
    "echo", "marin", "sage", "shimmer", "verse",
]

DEFAULT_SETTINGS = {
    "enabled_personas": ["albert", "albertine", "alex"],
    "interaction_mode": "vad",  # "vad" (freihaendig) oder "push_to_talk" (Leertaste)
    "show_debug_info": False,  # z.B. Audio-Chunk-Zaehler im Gespraech
    "printing_enabled": False,
    "selected_printer": "",  # leer = kein Drucker ausgewaehlt
    "board_item_limit": 15,  # neueste N Challenges bzw. N Wuensche auf dem Themen-Board
    "persona_voices": {"albert": "ash", "albertine": "shimmer", "alex": "alloy"},
}


def printing_active(settings: dict) -> bool:
    """Drucken ist nur wirklich aktiv, wenn beides gesetzt ist."""
    return bool(settings.get("printing_enabled")) and bool(settings.get("selected_printer"))


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
