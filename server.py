import asyncio
import base64
import json
import logging
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from personas import PERSONAS, greeting_instructions
from realtime_client import RealtimeClient
from tools import airtable_client
from tools.definitions import CONFIRM_PRINT_TOOL, TOOLS, dispatch as dispatch_tool
from tools.printing import list_printers, print_test_page, print_wunschzettel_directly
from tools.settings import load_settings, printing_active, save_settings
from tools.text_utils import swiss_de
from tools.wunschzettel_pdf import build_wunschzettel_pdf

LOG_FILE = Path(__file__).resolve().parent / "data" / "albert.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
logger = logging.getLogger("albert.web")

app = FastAPI()


@app.middleware("http")
async def no_cache_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


def _detect_version() -> str:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "unbekannt"


@app.get("/api/version")
async def api_version():
    return {"version": _detect_version()}


@app.get("/api/settings")
async def api_get_settings():
    return load_settings()


@app.post("/api/settings")
async def api_set_settings(payload: dict):
    enabled = payload.get("enabled_personas")
    mode = payload.get("interaction_mode")
    if not isinstance(enabled, list) or not enabled:
        raise HTTPException(status_code=400, detail="Mindestens eine Person muss aktiv sein.")
    enabled = [p for p in enabled if p in PERSONAS]
    if not enabled:
        raise HTTPException(status_code=400, detail="Ungueltige Personen-Auswahl.")
    if mode not in ("vad", "push_to_talk"):
        raise HTTPException(status_code=400, detail="Ungueltiger Modus.")
    show_debug_info = bool(payload.get("show_debug_info", False))
    selected_printer = payload.get("selected_printer") or ""
    if selected_printer and selected_printer not in list_printers():
        raise HTTPException(status_code=400, detail="Unbekannter Drucker.")
    try:
        board_item_limit = int(payload.get("board_item_limit", 15))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Ungueltige Anzahl fuer das Themen-Board.")
    if not 1 <= board_item_limit <= 50:
        raise HTTPException(status_code=400, detail="Anzahl muss zwischen 1 und 50 liegen.")
    settings = {
        "enabled_personas": enabled,
        "interaction_mode": mode,
        "show_debug_info": show_debug_info,
        "printing_enabled": bool(payload.get("printing_enabled", False)),
        "selected_printer": selected_printer,
        "board_item_limit": board_item_limit,
    }
    save_settings(settings)
    return settings


@app.get("/api/printers")
async def api_printers():
    return {"printers": list_printers()}


@app.post("/api/print-test")
async def api_print_test(payload: dict):
    printer_name = payload.get("printer_name") or ""
    if not printer_name or printer_name not in list_printers():
        raise HTTPException(status_code=400, detail="Kein gueltiger Drucker ausgewaehlt.")
    try:
        print_test_page(printer_name)
    except Exception:
        logger.exception("Testseite fehlgeschlagen (%s)", printer_name)
        raise HTTPException(status_code=500, detail="Testseite konnte nicht gedruckt werden.")
    return {"status": "ok"}


@app.get("/api/board")
async def api_board():
    limit = load_settings().get("board_item_limit", 15)
    challenges = await airtable_client.list_recent_entries("challenge", limit)
    wishes = await airtable_client.list_recent_entries("future_wish", limit)
    for entry in challenges:
        entry["entity_type"] = "challenge"
    for entry in wishes:
        entry["entity_type"] = "future_wish"
    return {"challenges": challenges, "wishes": wishes}


@app.delete("/api/board/{record_id}")
async def api_board_delete(record_id: str):
    try:
        await airtable_client.update_record("_input_pipeline", record_id, {"triage_status": "rejected"})
    except Exception:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    return {"status": "ok"}


@app.get("/api/wish/{record_id}")
async def api_wish(record_id: str):
    try:
        record = await airtable_client.get_record("_input_pipeline", record_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Wunsch nicht gefunden.")
    fields = record.get("fields", {})
    return {
        "id": record.get("id"),
        "created_time": record.get("createdTime"),
        "name": fields.get("name", ""),
        "about": fields.get("about", ""),
    }


async def _build_pdf_for_record(record_id: str) -> bytes:
    try:
        record = await airtable_client.get_record("_input_pipeline", record_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Wunsch nicht gefunden.")
    fields = record.get("fields", {})
    return build_wunschzettel_pdf(
        name=fields.get("name", ""),
        about=fields.get("about", ""),
        created_time=record.get("createdTime", ""),
        record_id=record.get("id", record_id),
    )


@app.get("/api/wish/{record_id}/pdf")
async def api_wish_pdf(record_id: str):
    pdf_bytes = await _build_pdf_for_record(record_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="wunschzettel-{record_id}.pdf"'},
    )


async def _print_record(record_id: str) -> None:
    """Wirft eine Exception bei jedem Fehler (kein Drucker, Druckfehler etc.).
    Druckt direkt per GDI, nicht ueber eine PDF-Datei -- keine externe
    Anwendung wird dafuer geoeffnet."""
    settings = load_settings()
    if not printing_active(settings):
        raise RuntimeError("Drucken ist nicht aktiviert.")
    try:
        record = await airtable_client.get_record("_input_pipeline", record_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Wunsch nicht gefunden.")
    fields = record.get("fields", {})
    print_wunschzettel_directly(
        printer_name=settings["selected_printer"],
        name=fields.get("name", ""),
        about=fields.get("about", ""),
        created_time=record.get("createdTime", ""),
        record_id=record.get("id", record_id),
    )


@app.post("/api/wish/{record_id}/print")
async def api_wish_print(record_id: str):
    try:
        await _print_record(record_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Drucken fehlgeschlagen (%s)", record_id)
        raise HTTPException(status_code=500, detail="Drucken fehlgeschlagen.")
    return {"status": "ok"}


@app.websocket("/ws/{persona_id}")
async def albert_socket(websocket: WebSocket, persona_id: str):
    await websocket.accept()

    persona = PERSONAS.get(persona_id)
    if persona is None:
        await websocket.send_text(json.dumps({"type": "error", "message": "Unbekannte Person."}))
        await websocket.close()
        return

    settings = load_settings()
    push_to_talk = settings.get("interaction_mode") == "push_to_talk"
    printing_on = printing_active(settings)

    async def send_audio(pcm_bytes: bytes):
        await websocket.send_text(
            json.dumps({"type": "audio", "audio": base64.b64encode(pcm_bytes).decode("ascii")})
        )

    def send_transcript(delta: str):
        asyncio.create_task(
            websocket.send_text(json.dumps({"type": "transcript", "delta": swiss_de(delta)}))
        )

    def send_response_start():
        asyncio.create_task(websocket.send_text(json.dumps({"type": "assistant_start"})))

    def send_user_transcript(transcript: str):
        asyncio.create_task(
            websocket.send_text(json.dumps({"type": "user_message", "text": swiss_de(transcript)}))
        )

    def send_speech_started():
        asyncio.create_task(websocket.send_text(json.dumps({"type": "user_speaking"})))

    ENTRY_ENTITY_TYPE = {
        "submit_wish": "future_wish",
        "submit_challenge": "challenge",
    }

    last_wish_record_id = None

    async def handle_tool_call(name: str, arguments: dict) -> str:
        nonlocal last_wish_record_id
        logger.info("Tool-Aufruf: %s(%s)", name, arguments)

        if name == "confirm_print":
            if not last_wish_record_id:
                return json.dumps({"error": "Kein Wunsch zum Ausdrucken vorhanden."})
            try:
                await _print_record(last_wish_record_id)
            except Exception:
                logger.exception("Drucken fehlgeschlagen (%s)", last_wish_record_id)
                await websocket.send_text(
                    json.dumps({"type": "print_status", "status": "error"})
                )
                return json.dumps({"error": "Drucken fehlgeschlagen."})
            await websocket.send_text(json.dumps({"type": "print_status", "status": "ok"}))
            return json.dumps({"status": "ok"})

        result = await dispatch_tool(name, arguments)

        if name in ("submit_wish", "submit_challenge"):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                parsed = {}
            if parsed.get("status") == "ok":
                if name == "submit_wish":
                    last_wish_record_id = parsed.get("record_id")
                display_name = arguments.get("name") or arguments.get("title", "")
                entity_type = ENTRY_ENTITY_TYPE.get(name, "")
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "new_entry",
                            "name": display_name,
                            "entity_type": entity_type,
                            "table": parsed.get("table"),
                            "record_id": parsed.get("record_id"),
                        }
                    )
                )
                if name == "submit_wish" and printing_on:
                    await websocket.send_text(
                        json.dumps({"type": "print_link", "record_id": parsed.get("record_id")})
                    )

        return result

    client = RealtimeClient(
        on_audio_delta=send_audio,
        on_transcript_delta=send_transcript,
        on_response_start=send_response_start,
        on_user_transcript=send_user_transcript,
        on_tool_call=handle_tool_call,
        on_speech_started=send_speech_started,
    )

    session_tools = TOOLS + [CONFIRM_PRINT_TOOL] if printing_on else TOOLS

    try:
        await client.connect(
            voice=persona.voice,
            instructions=persona.system_instructions(printing_enabled=printing_on),
            tools=session_tools,
            push_to_talk=push_to_talk,
        )
    except Exception:
        logger.exception("Verbindungsaufbau zur Realtime-API fehlgeschlagen (%s)", persona.name)
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Verbindung zu Albert fehlgeschlagen."})
        )
        await websocket.close()
        return

    await websocket.send_text(json.dumps({"type": "status", "status": "ready", "persona": persona.name}))
    await client.create_response(instructions=greeting_instructions(push_to_talk))

    audio_chunk_count = 0
    audio_byte_total = 0

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "audio_chunk":
                pcm_bytes = base64.b64decode(message["audio"])
                await client.append_audio(pcm_bytes)
                audio_chunk_count += 1
                audio_byte_total += len(pcm_bytes)
                if audio_chunk_count % 50 == 0:
                    logger.info(
                        "Audio-Stream: %d Chunks empfangen, %d Bytes insgesamt",
                        audio_chunk_count,
                        audio_byte_total,
                    )
            elif msg_type == "commit":
                await client.commit_and_respond()
            elif msg_type == "interrupt":
                await client.cancel_response()
    except WebSocketDisconnect:
        logger.info("Browser-Verbindung getrennt (%s)", persona.name)
    except Exception:
        logger.exception("Fehler in Albert-WebSocket-Session (%s)", persona.name)
    finally:
        await client.close()


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
