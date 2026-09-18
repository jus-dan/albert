import os

import httpx

from config import AIRTABLE_BASE_ID

AIRTABLE_API_TOKEN = os.getenv("AIRTABLE_API_TOKEN")

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {AIRTABLE_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _escape_formula_text(value: str) -> str:
    """Nur fuer die Interpolation in filterByFormula -- Anfuehrungszeichen
    und Backslashes wuerden die Formel zerschiessen. Die Suchanfrage kommt
    live aus Sprache, also nie ungefiltert einsetzen."""
    return (value or "").replace("\\", "").replace('"', "").replace("'", "").strip()[:60]


_REGEX_SPECIAL_CHARS = ".^$*+?()[]{}|"


def _word_boundary_pattern(query: str) -> str:
    """Baut ein REGEX_MATCH-Muster mit Wortgrenzen (\\b...\\b) statt
    einfachem SEARCH() -- SEARCH() ist reine Teilstring-Suche und faende
    z.B. bei der Anfrage "velo" auch "development" (enthaelt "velo" als
    Teilstring), was live getestet und bestaetigt wurde."""
    safe = _escape_formula_text(query)
    escaped = "".join(f"\\{ch}" if ch in _REGEX_SPECIAL_CHARS else ch for ch in safe)
    return rf"\b{escaped}\b"


_PIPELINE_ACTIVE = "NOT(OR({triage_status}='rejected', {triage_status}='duplicate'))"


async def submit_contribution(
    entity_type: str,
    name: str,
    about: str,
    contact_email: str = "",
    website: str = "",
    raw_text: str = "",
    event_location: str = "",
    start_date_time: str = "",
    end_date_time: str = "",
    challenge_framing: str = "",
) -> dict:
    fields: dict = {
        "name": name,
        "entity_type": entity_type,
        "about": about,
        "source": "web_albert",
        "triage_status": "new",
    }
    if contact_email:
        fields["contact_email"] = contact_email
    if website:
        fields["website"] = website
    if raw_text:
        fields["raw_text"] = raw_text
    if event_location:
        fields["event_location"] = event_location
    if start_date_time:
        fields["start_date_time"] = start_date_time
    if end_date_time:
        fields["end_date_time"] = end_date_time
    if challenge_framing:
        fields["challenge_framing"] = challenge_framing

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{BASE_URL}/_input_pipeline",
            headers=_headers(),
            json={"fields": fields},
        )
        resp.raise_for_status()
        data = resp.json()

    return {"table": "_input_pipeline", "record_id": data.get("id")}


async def get_record(table: str, record_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/{table}/{record_id}", headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def update_record(table: str, record_id: str, fields: dict) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{BASE_URL}/{table}/{record_id}",
            headers=_headers(),
            json={"fields": fields},
        )
        resp.raise_for_status()


async def list_recent_entries(challenge_framing: str, limit: int) -> list[dict]:
    """Neueste _input_pipeline-Eintraege eines Typs (challenge/future_wish),
    live aus Airtable -- schliesst abgelehnte/doppelte Eintraege aus.
    Direkt aus der Datenbank gelesen, kein lokaler Cache, der veralten
    koennte."""
    formula = f"AND({{challenge_framing}}='{challenge_framing}', {_PIPELINE_ACTIVE})"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/_input_pipeline",
            headers=_headers(),
            params={"filterByFormula": formula, "maxRecords": 100},
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])

    records.sort(key=lambda r: r.get("createdTime", ""), reverse=True)
    results = []
    for r in records[:limit]:
        fields = r.get("fields", {})
        results.append(
            {
                "id": r.get("id"),
                "label": fields.get("name", ""),
                "timestamp": r.get("createdTime", ""),
            }
        )
    return results


async def search_published(table: str, query: str, limit: int = 2) -> list[dict]:
    """Veroeffentlichte Eintraege einer Oekosystem-Tabelle (organizations/
    initiatives) zu einem Stichwort. NUR publish_status='published' --
    ungeprüfte, verworfene oder archivierte Eintraege duerfen Besuchern nie
    vorgelesen werden. Gibt bei jedem Fehler eine leere Liste zurueck, statt
    eine laufende Sprachantwort abzuwuergen."""
    if not query or not query.strip():
        return []
    pattern = _word_boundary_pattern(query)
    formula = (
        f"AND({{publish_status}}='published', OR("
        f'REGEX_MATCH(LOWER({{name}}&""), "{pattern}"), '
        f'REGEX_MATCH(LOWER({{description}}&""), "{pattern}"), '
        f'REGEX_MATCH(LOWER(ARRAYJOIN({{topics}}, ", ")), "{pattern}")))'
    )
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{BASE_URL}/{table}",
                headers=_headers(),
                params={"filterByFormula": formula, "maxRecords": limit},
            )
            resp.raise_for_status()
            records = resp.json().get("records", [])
    except Exception:
        return []

    results = []
    for r in records[:limit]:
        fields = r.get("fields", {})
        results.append(
            {
                "name": fields.get("name", ""),
                "description": (fields.get("description", "") or "")[:200],
                "website": fields.get("website", ""),
                "location": fields.get("location", ""),
            }
        )
    return results


async def search_pipeline_entries(query: str, limit: int = 2) -> list[dict]:
    """Bereits erfasste Wuensche/Anliegen anderer Besucher zu einem
    Stichwort (thematisch passend, nicht einfach die neuesten -- dafuer
    gibt es list_recent_entries). Schliesst abgelehnte/doppelte aus."""
    if not query or not query.strip():
        return []
    pattern = _word_boundary_pattern(query)
    formula = (
        f"AND({_PIPELINE_ACTIVE}, OR("
        f'REGEX_MATCH(LOWER({{name}}&""), "{pattern}"), '
        f'REGEX_MATCH(LOWER({{about}}&""), "{pattern}")))'
    )
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{BASE_URL}/_input_pipeline",
                headers=_headers(),
                params={"filterByFormula": formula, "maxRecords": limit},
            )
            resp.raise_for_status()
            records = resp.json().get("records", [])
    except Exception:
        return []

    results = []
    for r in records[:limit]:
        fields = r.get("fields", {})
        results.append(
            {
                "label": fields.get("name", ""),
                "framing": fields.get("challenge_framing", ""),
            }
        )
    return results
