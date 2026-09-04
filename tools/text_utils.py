from datetime import datetime

MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def swiss_de(text: str) -> str:
    """Schweizer Hochdeutsch kennt kein 'ß' -- immer 'ss'."""
    return text.replace("ß", "ss") if text else text


def split_about(about: str) -> tuple[str, str]:
    marker = "Konkrete lokale Idee:"
    idx = about.find(marker)
    wish_section = about if idx == -1 else about[:idx]
    # Beide Schreibweisen abfangen (aeltere Eintraege wurden noch mit dem
    # ASCII-Ersatz "Urspruenglicher" statt "Ursprünglicher" geschrieben).
    wish = wish_section.replace("Ursprünglicher Wunsch:", "").replace("Urspruenglicher Wunsch:", "").strip()
    idea = "" if idx == -1 else about[idx + len(marker):].strip()
    return wish, idea


def format_timestamp(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"{dt.day}. {MONTHS_DE[dt.month - 1]} {dt.year} · {dt.hour:02d}:{dt.minute:02d} Uhr"
    except Exception:
        return ""
