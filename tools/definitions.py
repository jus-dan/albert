import json

from tools import airtable_client, events
from tools.text_utils import swiss_de

TOOLS = [
    {
        "type": "function",
        "name": "submit_wish",
        "description": (
            "Erfasst einen Zukunftswunsch zur spaeteren Pruefung durch das Team: "
            "den urspruenglichen Wunsch der Person und, falls sie selbst eine "
            "gefunden hat, ihre eigene konkrete lokale Idee dazu. Rufe dies erst "
            "auf, NACHDEM du der Person durch Fragen Gelegenheit gegeben hast, "
            "vom abstrakten Wunsch zu einer eigenen konkreten Idee zu kommen -- "
            "nicht schon beim ersten, noch abstrakten Wunsch. Wenn der Person "
            "trotz Rueckfrage keine eigene Idee einfaellt, erfasse einfach nur "
            "den Wunsch, ohne local_idea."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Kurzer, praegnanter Titel -- der lokalen Idee, oder sonst des Wunsches selbst.",
                },
                "original_wish": {
                    "type": "string",
                    "description": "Der Wunsch, so wie die Person ihn zuerst geaeussert hat, z.B. 'Weltfrieden'.",
                },
                "local_idea": {
                    "type": "string",
                    "description": (
                        "Die von der Person SELBST entwickelte konkrete, lokale "
                        "Idee bzw. Handlung, die auf diesen Wunsch einzahlt. Nur "
                        "ausfuellen, wenn die Idee wirklich von der Person kam, "
                        "nicht von dir. Sonst weglassen."
                    ),
                },
                "contact_name": {
                    "type": "string",
                    "description": "Name der Person, falls freiwillig genannt (optional).",
                },
            },
            "required": ["title", "original_wish"],
        },
    },
    {
        "type": "function",
        "name": "submit_challenge",
        "description": (
            "Erfasst ein Anliegen oder eine Beobachtung, die die Person "
            "beschaeftigt (kein Wunsch), zur spaeteren Pruefung durch das "
            "Team -- damit sichtbar wird, was die Leute gerade umtreibt. "
            "Nutze dies, wenn die Person kein Zukunftswunsch, sondern eine "
            "Sorge, ein Problem oder eine Beobachtung teilt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Kurzer, praegnanter Titel fuer das Anliegen.",
                },
                "description": {
                    "type": "string",
                    "description": "Was die Person beschaeftigt oder beobachtet hat, so wie sie es erzaehlt hat.",
                },
                "contact_name": {
                    "type": "string",
                    "description": "Name der Person, falls freiwillig genannt (optional).",
                },
            },
            "required": ["title", "description"],
        },
    },
]


async def dispatch(name: str, arguments: dict) -> str:
    if name == "submit_wish":
        title = swiss_de(arguments.get("title", ""))
        original_wish = swiss_de(arguments.get("original_wish", ""))
        local_idea = swiss_de(arguments.get("local_idea", ""))
        if not title.strip() or not original_wish.strip():
            return json.dumps(
                {"error": "title und original_wish duerfen nicht leer sein -- bitte nochmal aufrufen."}
            )
        about = f"Urspruenglicher Wunsch: {original_wish}"
        if local_idea:
            about += f"\n\nKonkrete lokale Idee: {local_idea}"
        result = await airtable_client.submit_contribution(
            entity_type="future_action",
            name=title,
            about=about,
            contact_email="",
            website="",
            raw_text=about,
            challenge_framing="future_wish",
        )
        contact_name = arguments.get("contact_name", "")
        events.log_event("contribution", "future_wish", f"{title}" + (f" ({contact_name})" if contact_name else ""))
        return json.dumps(
            {"status": "ok", "table": result["table"], "record_id": result["record_id"]}
        )

    if name == "submit_challenge":
        title = swiss_de(arguments.get("title", ""))
        description = swiss_de(arguments.get("description", ""))
        if not title.strip() or not description.strip():
            return json.dumps(
                {"error": "title und description duerfen nicht leer sein -- bitte nochmal aufrufen."}
            )
        result = await airtable_client.submit_contribution(
            entity_type="challenge",
            name=title,
            about=description,
            contact_email="",
            website="",
            raw_text=description,
            challenge_framing="challenge",
        )
        contact_name = arguments.get("contact_name", "")
        events.log_event("contribution", "challenge", f"{title}" + (f" ({contact_name})" if contact_name else ""))
        return json.dumps(
            {"status": "ok", "table": result["table"], "record_id": result["record_id"]}
        )

    return json.dumps({"error": f"Unbekanntes Tool: {name}"})
