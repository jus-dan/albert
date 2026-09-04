import asyncio
import base64
import json
import logging
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from personas import GREETING_INSTRUCTIONS, PERSONAS
from realtime_client import RealtimeClient
from tools import airtable_client, events
from tools.definitions import TOOLS, dispatch as dispatch_tool
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


@app.get("/api/board")
async def api_board():
    return {
        "challenges": events.recent_events_by_entity("contribution", "challenge", limit=30),
        "wishes": events.recent_events_by_entity("contribution", "future_wish", limit=30),
    }


@app.delete("/api/board/{event_id}")
async def api_board_delete(event_id: str):
    if not events.delete_event(event_id):
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


@app.get("/api/wish/{record_id}/pdf")
async def api_wish_pdf(record_id: str):
    try:
        record = await airtable_client.get_record("_input_pipeline", record_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Wunsch nicht gefunden.")
    fields = record.get("fields", {})
    pdf_bytes = build_wunschzettel_pdf(
        name=fields.get("name", ""),
        about=fields.get("about", ""),
        created_time=record.get("createdTime", ""),
        record_id=record.get("id", record_id),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="wunschzettel-{record_id}.pdf"'},
    )


@app.websocket("/ws/{persona_id}")
async def albert_socket(websocket: WebSocket, persona_id: str):
    await websocket.accept()

    persona = PERSONAS.get(persona_id)
    if persona is None:
        await websocket.send_text(json.dumps({"type": "error", "message": "Unbekannte Person."}))
        await websocket.close()
        return

    async def send_audio(pcm_bytes: bytes):
        await websocket.send_text(
            json.dumps({"type": "audio", "audio": base64.b64encode(pcm_bytes).decode("ascii")})
        )

    def send_transcript(delta: str):
        asyncio.create_task(websocket.send_text(json.dumps({"type": "transcript", "delta": delta})))

    def send_response_start():
        asyncio.create_task(websocket.send_text(json.dumps({"type": "assistant_start"})))

    def send_user_transcript(transcript: str):
        asyncio.create_task(websocket.send_text(json.dumps({"type": "user_message", "text": transcript})))

    def send_speech_started():
        asyncio.create_task(websocket.send_text(json.dumps({"type": "user_speaking"})))

    ENTRY_ENTITY_TYPE = {
        "submit_wish": "future_wish",
        "submit_challenge": "challenge",
    }

    async def handle_tool_call(name: str, arguments: dict) -> str:
        logger.info("Tool-Aufruf: %s(%s)", name, arguments)

        result = await dispatch_tool(name, arguments)

        if name in ("submit_wish", "submit_challenge"):
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                parsed = {}
            if parsed.get("status") == "ok":
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
                if name == "submit_wish":
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

    try:
        await client.connect(
            voice=persona.voice,
            instructions=persona.system_instructions(),
            tools=TOOLS,
        )
    except Exception:
        logger.exception("Verbindungsaufbau zur Realtime-API fehlgeschlagen (%s)", persona.name)
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Verbindung zu Albert fehlgeschlagen."})
        )
        await websocket.close()
        return

    await websocket.send_text(json.dumps({"type": "status", "status": "ready", "persona": persona.name}))
    await client.create_response(instructions=GREETING_INSTRUCTIONS)

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
