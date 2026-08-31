import asyncio
import logging
import sys

import keyboard

from audio_io import MicRecorder, SpeakerPlayer
from config import OPENAI_API_KEY, PUSH_TO_TALK_KEY
from realtime_client import RealtimeClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("albert")


async def main():
    if not OPENAI_API_KEY:
        print(
            "Fehler: OPENAI_API_KEY ist nicht gesetzt.\n"
            "Kopiere .env.example zu .env und trage dort deinen OpenAI API-Key ein."
        )
        sys.exit(1)

    speaker = SpeakerPlayer()
    mic = MicRecorder()

    def on_transcript(delta: str):
        print(delta, end="", flush=True)

    client = RealtimeClient(on_audio_delta=speaker.enqueue, on_transcript_delta=on_transcript)

    print("Verbinde mit Albert ...")
    await client.connect()
    print(f"Verbunden. Halte [{PUSH_TO_TALK_KEY}] gedrueckt, um zu sprechen. Strg+C zum Beenden.")

    playback_task = asyncio.create_task(speaker.run())

    key_down = asyncio.Event()
    key_up = asyncio.Event()
    loop = asyncio.get_running_loop()

    def handle_press(_event):
        loop.call_soon_threadsafe(key_down.set)

    def handle_release(_event):
        loop.call_soon_threadsafe(key_up.set)

    keyboard.on_press_key(PUSH_TO_TALK_KEY, handle_press)
    keyboard.on_release_key(PUSH_TO_TALK_KEY, handle_release)

    try:
        while True:
            key_down.clear()
            await key_down.wait()

            key_up.clear()
            mic.start()
            print("\n[Albert hoert zu ...]")

            while not key_up.is_set():
                await asyncio.sleep(0.05)
                chunk = mic.read_available()
                if chunk:
                    await client.append_audio(chunk)

            mic.stop()
            chunk = mic.read_available()
            if chunk:
                await client.append_audio(chunk)

            print("[Albert antwortet ...]")
            await client.commit_and_respond()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        keyboard.unhook_all()
        await client.close()
        speaker.close()
        playback_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBeendet.")
