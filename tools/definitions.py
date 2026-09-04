import json

from tools import airtable_client, events

TOOLS = [
    {
        "type": "function",
        "name": "submit_wish",
        "description": (
            "Erfasst einen Zukunftswunsch zur spaeteren Pruefung durch das Team: "
            "den urspruenglichen Wunsch der Person UND die gemeinsam entwickelte "
            "konkrete, lokale Idee dazu. Rufe dies erst auf, NACHDEM du mit der "
            "Person vom abstrakten Wunsch zu einer konkreten lokalen Idee "
            "gekommen bist -- nicht schon beim ersten, noch abstrakten Wunsch."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Kurzer, praegnanter Titel fuer die lokale Idee.",
                },
                "original_wish": {
                    "type": "string",
                    "description": "Der Wunsch, so wie die Person ihn zuerst geaeussert hat, z.B. 'Weltfrieden'.",
                },
                "local_idea": {
                    "type": "string",
                    "description": (
                        "Die gemeinsam entwickelte konkrete, lokale Idee bzw. "
                        "Handlung, die auf diesen Wunsch einzahlt."
                    ),
                },
                "contact_name": {
                    "type": "string",
                    "description": "Name der Person, falls freiwillig genannt (optional).",
                },
            },
            "required": ["title", "original_wish", "local_idea"],
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

    if name == "submit_wish":
        title = arguments.get("title", "")
        original_wish = arguments.get("original_wish", "")
        local_idea = arguments.get("local_idea", "")
        about = f"Urspruenglicher Wunsch: {original_wish}\n\nKonkrete lokale Idee: {local_idea}"
        result = await airtable_client.submit_contribution(
            entity_type="challenge",
            name=title,
            about=about,
            contact_email="",
            website="",
            raw_text=about,
            challenge_framing="future_wish",
        )
        contact_name = arguments.get("contact_name", "")
        events.log_event("contribution", "challenge", f"{title}" + (f" ({contact_name})" if contact_name else ""))
        return json.dumps(
            {"status": "ok", "table": result["table"], "record_id": result["record_id"]}
        )

    return json.dumps({"error": f"Unbekanntes Tool: {name}"})
