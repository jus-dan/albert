import httpx

from config import OPENAI_API_KEY

PREVIEW_TEXT = (
    "Hallo, ich bin's. So klingt meine Stimme, wenn wir miteinander sprechen."
)


async def generate_voice_preview(voice: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini-tts",
                "voice": voice,
                "input": PREVIEW_TEXT,
                "response_format": "mp3",
            },
        )
        response.raise_for_status()
        return response.content
