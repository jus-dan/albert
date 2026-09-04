import json

from tools import airtable_client
from tools.text_utils import swiss_de

TOOLS = [
    {
        "type": "function",
        "name": "submit_wish",
        "description": (
            "Erfasst einen Zukunftswunsch zur späteren Prüfung durch das Team: "
            "den ursprünglichen Wunsch der Person und, falls sie selbst eine "
            "gefunden hat, ihre eigene konkrete lokale Idee dazu. Rufe dies erst "
            "auf, NACHDEM du der Person durch Fragen Gelegenheit gegeben hast, "
            "vom abstrakten Wunsch zu einer eigenen konkreten Idee zu kommen -- "
            "nicht schon beim ersten, noch abstrakten Wunsch. Wenn der Person "
            "trotz Rückfrage keine eigene Idee einfällt, erfasse einfach nur "
            "den Wunsch, ohne local_idea."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Kurzer, prägnanter Titel -- der lokalen Idee, oder sonst des Wunsches selbst.",
                },
                "original_wish": {
                    "type": "string",
                    "description": "Der Wunsch, so wie die Person ihn zuerst geäussert hat, z.B. 'Weltfrieden'.",
                },
                "why": {
                    "type": "string",
                    "description": (
                        "Was sich hier vor Ort veraendern wuerde bzw. warum der "
                        "Person dieser Wunsch wichtig ist -- ihre Antwort auf die "
                        "erste Rueckfrage im Gespraech. Nur ausfuellen, wenn die "
                        "Person dazu wirklich etwas gesagt hat."
                    ),
                },
                "local_idea": {
                    "type": "string",
                    "description": (
                        "Die von der Person SELBST entwickelte konkrete, lokale "
                        "Idee bzw. Handlung, die auf diesen Wunsch einzahlt. Nur "
                        "ausfüllen, wenn die Idee wirklich von der Person kam, "
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
            "beschäftigt (kein Wunsch), zur späteren Prüfung durch das "
            "Team -- damit sichtbar wird, was die Leute gerade umtreibt. "
            "Nutze dies, wenn die Person kein Zukunftswunsch, sondern eine "
            "Sorge, ein Problem oder eine Beobachtung teilt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Kurzer, prägnanter Titel für das Anliegen.",
                },
                "description": {
                    "type": "string",
                    "description": "Was die Person beschäftigt oder beobachtet hat, so wie sie es erzählt hat.",
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

CONFIRM_PRINT_TOOL = {
    "type": "function",
    "name": "confirm_print",
    "description": (
        "Loest den echten Druckauftrag fuer den zuletzt erfassten Wunsch "
        "aus. Rufe dies SOFORT auf, sobald die Person auf deine Frage "
        "'Moechtest du deinen Wunsch ausdrucken?' mit Ja antwortet -- das "
        "ist die Aktion selbst, nicht nur eine Ankuendigung. Bei Nein "
        "nicht aufrufen."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


async def dispatch(name: str, arguments: dict) -> str:
    if name == "submit_wish":
        title = swiss_de(arguments.get("title", ""))
        original_wish = swiss_de(arguments.get("original_wish", ""))
        why = swiss_de(arguments.get("why", ""))
        local_idea = swiss_de(arguments.get("local_idea", ""))
        if not title.strip() or not original_wish.strip():
            return json.dumps(
                {"error": "title und original_wish dürfen nicht leer sein -- bitte nochmal aufrufen."}
            )
        about = f"Ursprünglicher Wunsch: {original_wish}"
        if why:
            about += f"\n\nWarum: {why}"
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
        return json.dumps(
            {"status": "ok", "table": result["table"], "record_id": result["record_id"]}
        )

    if name == "submit_challenge":
        title = swiss_de(arguments.get("title", ""))
        description = swiss_de(arguments.get("description", ""))
        if not title.strip() or not description.strip():
            return json.dumps(
                {"error": "title und description dürfen nicht leer sein -- bitte nochmal aufrufen."}
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
        return json.dumps(
            {"status": "ok", "table": result["table"], "record_id": result["record_id"]}
        )

    return json.dumps({"error": f"Unbekanntes Tool: {name}"})
