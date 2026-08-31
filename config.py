import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REALTIME_MODEL = os.getenv("ALBERT_MODEL", "gpt-realtime")
VOICE = os.getenv("ALBERT_VOICE", "marin")
PUSH_TO_TALK_KEY = os.getenv("ALBERT_PTT_KEY", "space")

SAMPLE_RATE = 24000
CHANNELS = 1

ALBERT_INSTRUCTIONS = (
    "Du bist Albert, ein hilfreicher, freundlicher Sprachassistent, der lokal auf dem "
    "Rechner des Nutzers laeuft. Antworte auf Deutsch, klar und in natuerlicher, "
    "gesprochener Sprache. Halte deine Antworten kurz und konversationell, es sei denn, "
    "der Nutzer bittet ausdruecklich um mehr Details."
)
