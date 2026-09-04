from datetime import datetime

MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def swiss_de(text: str) -> str:
    """Schweizer Hochdeutsch kennt kein 'ß' -- immer 'ss'."""
    return text.replace("ß", "ss") if text else text


def split_about(about: str) -> tuple[str, str, str]:
    idea_marker = "Konkrete lokale Idee:"
    why_marker = "Warum:"

    idea_idx = about.find(idea_marker)
    before_idea = about if idea_idx == -1 else about[:idea_idx]
    idea = "" if idea_idx == -1 else about[idea_idx + len(idea_marker):].strip()

    why_idx = before_idea.find(why_marker)
    wish_section = before_idea if why_idx == -1 else before_idea[:why_idx]
    why = "" if why_idx == -1 else before_idea[why_idx + len(why_marker):].strip()

    # Beide Schreibweisen abfangen (aeltere Eintraege wurden noch mit dem
    # ASCII-Ersatz "Urspruenglicher" statt "Ursprünglicher" geschrieben).
    wish = wish_section.replace("Ursprünglicher Wunsch:", "").replace("Urspruenglicher Wunsch:", "").strip()
    return wish, why, idea


def format_timestamp(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"{dt.day}. {MONTHS_DE[dt.month - 1]} {dt.year} · {dt.hour:02d}:{dt.minute:02d} Uhr"
    except Exception:
        return ""
