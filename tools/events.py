import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

EVENTS_FILE = Path(__file__).resolve().parent.parent / "data" / "events.jsonl"


def log_event(kind: str, entity_type: str, label: str) -> None:
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": uuid.uuid4().hex,
        "kind": kind,
        "entity_type": entity_type,
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deleted": False,
    }
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _read_all() -> list[dict]:
    if not EVENTS_FILE.exists():
        return []
    entries = []
    with EVENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def recent_events(kind: str, limit: int = 30) -> list[dict]:
    matches = [e for e in _read_all() if e.get("kind") == kind and not e.get("deleted")]
    matches.reverse()
    return matches[:limit]


def recent_events_by_entity(kind: str, entity_type: str, limit: int = 30) -> list[dict]:
    matches = [
        e
        for e in _read_all()
        if e.get("kind") == kind and e.get("entity_type") == entity_type and not e.get("deleted")
    ]
    matches.reverse()
    return matches[:limit]


def delete_event(event_id: str) -> bool:
    entries = _read_all()
    found = False
    for entry in entries:
        if entry.get("id") == event_id:
            entry["deleted"] = True
            found = True
            break

    if not found:
        return False

    with EVENTS_FILE.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return True
