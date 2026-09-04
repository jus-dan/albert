import os

import httpx

AIRTABLE_API_TOKEN = os.getenv("AIRTABLE_API_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {AIRTABLE_API_TOKEN}",
        "Content-Type": "application/json",
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


async def get_record(table: str, record_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/{table}/{record_id}", headers=_headers())
        resp.raise_for_status()
        return resp.json()
