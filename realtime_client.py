import asyncio
import base64
import json
import logging

import websockets

from config import ALBERT_INSTRUCTIONS, OPENAI_API_KEY, REALTIME_MODEL, SAMPLE_RATE, VOICE

logger = logging.getLogger("albert.realtime")

REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"


class RealtimeClient:
    """Thin wrapper around the OpenAI Realtime WebSocket API."""

    def __init__(
        self,
        on_audio_delta,
        on_transcript_delta=None,
        on_response_start=None,
        on_user_transcript=None,
        on_tool_call=None,
        on_speech_started=None,
    ):
        self._on_audio_delta = on_audio_delta
        self._on_transcript_delta = on_transcript_delta
        self._on_response_start = on_response_start
        self._on_user_transcript = on_user_transcript
        self._on_tool_call = on_tool_call
        self._on_speech_started = on_speech_started
        self._ws = None
        self._recv_task = None
        self._response_active = False

    async def connect(
        self,
        voice: str | None = None,
        instructions: str | None = None,
        tools: list[dict] | None = None,
    ):
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        }
        self._ws = await websockets.connect(
            REALTIME_URL,
            additional_headers=headers,
            max_size=None,
        )
        session: dict = {
            "type": "realtime",
            "model": REALTIME_MODEL,
            "output_modalities": ["audio"],
            "instructions": instructions or ALBERT_INSTRUCTIONS,
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    # Server-seitige Sprachpausenerkennung: Mikro streamt
                    # durchgehend, kein Push-to-Talk noetig. create_response
                    # und interrupt_response bewusst aus -- wir loesen Antwort
                    # und Unterbrechung selbst explizit ueber die
                    # speech_started/speech_stopped-Events aus (Zeile unten),
                    # statt uns auf das automatische API-Verhalten zu verlassen.
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.4,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                        "create_response": False,
                        "interrupt_response": False,
                    },
                    "transcription": {"model": "gpt-4o-mini-transcribe"},
                },
                "output": {
                    "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                    "voice": voice or VOICE,
                },
            },
        }
        if tools:
            session["tools"] = tools
            session["tool_choice"] = "auto"

        await self._send({"type": "session.update", "session": session})
        self._recv_task = asyncio.create_task(self._receive_loop())

    async def close(self):
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws:
            await self._ws.close()

    async def _send(self, event: dict):
        await self._ws.send(json.dumps(event))

    async def append_audio(self, pcm_bytes: bytes):
        if not pcm_bytes:
            return
        await self._send(
            {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(pcm_bytes).decode("ascii"),
            }
        )

    async def create_response(self, instructions: str | None = None):
        event = {"type": "response.create"}
        if instructions:
            event["response"] = {"instructions": instructions}
        await self._send(event)

    async def cancel_response(self):
        await self._send({"type": "response.cancel"})

    async def _handle_tool_call(self, event: dict):
        call_id = event.get("call_id")
        name = event.get("name", "")
        try:
            arguments = json.loads(event.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}

        if self._on_tool_call is None:
            output = json.dumps({"error": "Keine Tools verfuegbar."})
        else:
            try:
                output = await self._on_tool_call(name, arguments)
            except Exception:
                logger.exception("Tool-Aufruf fehlgeschlagen: %s", name)
                output = json.dumps({"error": "Tool-Aufruf fehlgeschlagen."})

        await self._send(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": output,
                },
            }
        )
        await self.create_response()

    async def _receive_loop(self):
        try:
            async for raw in self._ws:
                event = json.loads(raw)
                event_type = event.get("type")

                if event_type == "response.output_audio.delta":
                    audio_bytes = base64.b64decode(event["delta"])
                    await self._on_audio_delta(audio_bytes)
                elif event_type == "response.output_audio_transcript.delta" and self._on_transcript_delta:
                    self._on_transcript_delta(event.get("delta", ""))
                elif event_type == "response.created":
                    self._response_active = True
                    if self._on_response_start:
                        self._on_response_start()
                elif event_type == "response.done":
                    self._response_active = False
                elif (
                    event_type == "conversation.item.input_audio_transcription.completed"
                    and self._on_user_transcript
                ):
                    self._on_user_transcript(event.get("transcript", ""))
                elif event_type == "response.function_call_arguments.done":
                    await self._handle_tool_call(event)
                elif event_type == "input_audio_buffer.speech_started":
                    logger.info("VAD: Sprache erkannt")
                    if self._on_speech_started:
                        self._on_speech_started()
                    if self._response_active:
                        await self.cancel_response()
                elif event_type == "input_audio_buffer.speech_stopped":
                    if self._response_active:
                        logger.info("VAD: Sprachende erkannt, aber schon eine Antwort aktiv -- ignoriere")
                    else:
                        logger.info("VAD: Sprachende erkannt, erzeuge Antwort")
                        await self.create_response()
                elif event_type == "error":
                    logger.error("Realtime-API-Fehler: %s", event.get("error"))
                elif event_type in ("session.created", "session.updated"):
                    logger.info("Session bereit (%s)", event_type)
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed:
            logger.info("Verbindung zur Realtime-API geschlossen.")
