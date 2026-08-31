import asyncio
import queue

import sounddevice as sd

from config import CHANNELS, SAMPLE_RATE


class MicRecorder:
    """Captures raw PCM16 audio from the microphone while active."""

    def __init__(self):
        self._queue: "queue.Queue[bytes]" = queue.Queue()
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            callback=self._callback,
        )

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[audio] Mikrofon-Status: {status}")
        self._queue.put(bytes(indata))

    def start(self):
        while not self._queue.empty():
            self._queue.get_nowait()
        self._stream.start()

    def stop(self):
        self._stream.stop()

    def read_available(self) -> bytes:
        chunks = []
        while not self._queue.empty():
            chunks.append(self._queue.get_nowait())
        return b"".join(chunks)


class SpeakerPlayer:
    """Plays back raw PCM16 audio chunks as they arrive from the model."""

    def __init__(self):
        self._queue: "asyncio.Queue[bytes | None]" = asyncio.Queue()
        self._stream = sd.RawOutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
        )
        self._stream.start()

    async def enqueue(self, pcm_bytes: bytes):
        await self._queue.put(pcm_bytes)

    async def run(self):
        while True:
            chunk = await self._queue.get()
            if chunk is None:
                break
            self._stream.write(chunk)

    def close(self):
        self._stream.stop()
        self._stream.close()
