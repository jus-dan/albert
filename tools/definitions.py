import json

from tools import airtable_client, events

TOOLS = [
    {
        "type": "function",
        "name": "list_entities",
        "description": (
            "Sucht vorhandene Eintraege im Oekosystem und gibt Name, Typ und "
            "Beschreibung zurueck. Durchsucht IMMER alle Kategorien gleichzeitig "
            "(Initiativen, Organisationen UND Personen) -- du musst den Typ nicht "
            "vorher erraten. Nutze dies, wenn der Nutzer wissen will, was es "
            "bereits gibt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Optionales Suchwort, z.B. ein Thema oder Name. Leer lassen, "
                        "um die neuesten Eintraege ganz allgemein zu zeigen."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "submit_contribution",
        "description": (
            "Erfasst einen neuen Beitrag (Organisation, Person, Initiative, "
            "Challenge oder Event), den der Nutzer erzaehlt hat, zur spaeteren "
            "Pruefung durch das Team. Nutze dies, wenn der Nutzer dir etwas Neues "
            "mitteilen moechte. Stelle je nach Typ passende Rueckfragen, bevor du "
            "das Tool aufrufst: bei einer Person z.B. nach Kontakt-E-Mail und "
            "Organisation, bei einem Event nach Ort und Datum/Zeit, bei einer "
            "Challenge, ob es eher ein akutes Problem oder ein Wunsch fuer die "
            "Zukunft ist, bei Organisation/Initiative nach der Website."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["organization", "person", "initiative", "challenge", "event"],
                    "description": "Um welche Art von Beitrag es sich handelt.",
                },
                "name": {
                    "type": "string",
                    "description": "Name der Organisation, Person, Initiative, Challenge oder des Events.",
                },
                "about": {
                    "type": "string",
                    "description": "Kurze Zusammenfassung dessen, was der Nutzer erzaehlt hat.",
                },
                "contact_email": {
                    "type": "string",
                    "description": "Kontakt-E-Mail, falls genannt (v.a. bei Personen).",
                },
                "website": {
                    "type": "string",
                    "description": "Website, falls genannt.",
                },
                "event_location": {
                    "type": "string",
                    "description": "Ort des Events, falls entity_type 'event' ist.",
                },
                "start_date_time": {
                    "type": "string",
                    "description": "Start-Datum/Zeit des Events, falls entity_type 'event' ist.",
                },
                "end_date_time": {
                    "type": "string",
                    "description": "End-Datum/Zeit des Events, falls entity_type 'event' ist.",
                },
                "challenge_framing": {
                    "type": "string",
                    "enum": ["challenge", "future_wish"],
                    "description": (
                        "Nur falls entity_type 'challenge' ist: 'challenge' fuer ein "
                        "akutes Problem, 'future_wish' fuer einen Wunsch/eine Idee "
                        "fuer die Zukunft."
                    ),
                },
            },
            "required": ["entity_type", "name", "about"],
        },
    },
]


async def dispatch(name: str, arguments: dict) -> str:
    if name == "list_entities":
        query = arguments.get("query", "")
        results = await airtable_client.search_all_entities(query=query)
        events.log_event("search", "all", query or "(alle)")
        if not results:
            return json.dumps({"count": 0, "results": []})
        return json.dumps({"count": len(results), "results": results})

    if name == "submit_contribution":
        result = await airtable_client.submit_contribution(
            entity_type=arguments.get("entity_type", ""),
            name=arguments.get("name", ""),
            about=arguments.get("about", ""),
            contact_email=arguments.get("contact_email", ""),
            website=arguments.get("website", ""),
            raw_text=arguments.get("about", ""),
            event_location=arguments.get("event_location", ""),
            start_date_time=arguments.get("start_date_time", ""),
            end_date_time=arguments.get("end_date_time", ""),
            challenge_framing=arguments.get("challenge_framing", ""),
        )
        events.log_event("contribution", arguments.get("entity_type", ""), arguments.get("name", ""))
        return json.dumps(
            {"status": "ok", "table": result["table"], "record_id": result["record_id"]}
        )

    return json.dumps({"error": f"Unbekanntes Tool: {name}"})
