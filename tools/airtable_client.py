import asyncio
import os

import httpx

AIRTABLE_API_TOKEN = os.getenv("AIRTABLE_API_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

TABLE_BY_ENTITY = {
    "initiative": "initiatives",
    "organization": "organizations",
    "person": "people",
}

# Welche (nicht-verknuepften) Felder pro Entitaetstyp fuer Antworten relevant
# sind. Verknuepfte Felder (multipleRecordLinks) liefern nur Record-IDs statt
# lesbarer Namen und werden daher hier bewusst ausgelassen.
ENTITY_FIELDS = {
    "initiative": ["name", "description", "website", "source_url", "topics", "start_date", "end_date"],
    "organization": ["name", "description", "website", "location", "topics"],
    "person": ["name", "description", "role", "website"],
}

MAX_RESULTS = 8


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {AIRTABLE_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _build_search_formula(query: str) -> str | None:
    if not query:
        return None
    safe_query = query.replace('"', '\\"')
    return f'SEARCH(LOWER("{safe_query}"), LOWER({{name}} & " " & {{description}}))'


async def _query_table(table: str, formula: str | None) -> list[dict]:
    params: dict = {"maxRecords": MAX_RESULTS}
    if formula:
        params["filterByFormula"] = formula

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/{table}", headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("records", [])


async def list_entities(entity_type: str, query: str = "") -> list[dict]:
    table = TABLE_BY_ENTITY.get(entity_type)
    if not table:
        return []
    wanted_fields = ENTITY_FIELDS.get(entity_type, ["name", "description"])
    formula = _build_search_formula(query)
    records = await _query_table(table, formula)

    results = []
    for record in records:
        fields = record.get("fields", {})
        entry = {f: fields[f] for f in wanted_fields if fields.get(f)}
        if entry.get("name"):
            entry["entity_type"] = entity_type
            results.append(entry)
    return results


async def search_all_entities(query: str = "") -> list[dict]:
    """Durchsucht alle Entitaets-Tabellen (Initiativen, Organisationen,
    Personen) gleichzeitig, damit eine Suche nicht an einem falsch geratenen
    Typ vorbeigeht."""
    entity_types = list(TABLE_BY_ENTITY.keys())
    results_per_type = await asyncio.gather(
        *(list_entities(entity_type, query) for entity_type in entity_types)
    )
    combined: list[dict] = []
    for results in results_per_type:
        combined.extend(results)
    return combined


async def search_debug(entity_type: str, query: str = "") -> dict:
    table = TABLE_BY_ENTITY.get(entity_type)
    if not table:
        return {"error": f"Unbekannter entity_type: {entity_type}"}
    wanted_fields = ENTITY_FIELDS.get(entity_type, ["name", "description"])
    formula = _build_search_formula(query)
    records = await _query_table(table, formula)

    results = []
    for record in records:
        fields = record.get("fields", {})
        entry = {f: fields[f] for f in wanted_fields if fields.get(f)}
        entry["_record_id"] = record.get("id")
        if entry.get("name"):
            results.append(entry)

    return {
        "table": table,
        "formula": formula,
        "max_results_cap": MAX_RESULTS,
        "count": len(results),
        "results": results,
    }


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


async def update_record(table: str, record_id: str, fields: dict) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{BASE_URL}/{table}/{record_id}",
            headers=_headers(),
            json={"fields": fields},
        )
        resp.raise_for_status()
