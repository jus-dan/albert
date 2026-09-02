import asyncio
import base64
import json
import logging
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from personas import GREETING_INSTRUCTIONS, PERSONAS
from realtime_client import RealtimeClient
from tools import airtable_client, events
from tools.definitions import TOOLS, dispatch as dispatch_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("albert.web")

app = FastAPI()


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


APP_VERSION = _detect_version()


@app.get("/api/version")
async def api_version():
    return {"version": APP_VERSION}


@app.get("/api/search")
async def api_search(entity_type: str, query: str = ""):
    return await airtable_client.search_debug(entity_type, query)


@app.get("/api/board")
async def api_board():
    return {
        "searches": events.recent_events("search", limit=30),
        "contributions": events.recent_events("contribution", limit=30),
    }


@app.delete("/api/board/{event_id}")
async def api_board_delete(event_id: str):
    if not events.delete_event(event_id):
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    return {"status": "ok"}


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

    async def handle_tool_call(name: str, arguments: dict) -> str:
        logger.info("Tool-Aufruf: %s(%s)", name, arguments)
        result = await dispatch_tool(name, arguments)

        if name == "submit_contribution":
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                parsed = {}
            if parsed.get("status") == "ok":
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "new_entry",
                            "name": arguments.get("name", ""),
                            "entity_type": arguments.get("entity_type", ""),
                            "table": parsed.get("table"),
                            "record_id": parsed.get("record_id"),
                        }
                    )
                )

        return result

    client = RealtimeClient(
        on_audio_delta=send_audio,
        on_transcript_delta=send_transcript,
        on_response_start=send_response_start,
        on_user_transcript=send_user_transcript,
        on_tool_call=handle_tool_call,
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

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "audio_chunk":
                await client.append_audio(base64.b64decode(message["audio"]))
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
