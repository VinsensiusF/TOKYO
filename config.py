"""Single place for every setting, read from .env so code never holds secrets."""
import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny|base|small
VOICES_DIR = os.getenv("VOICES_DIR", "voices")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "id")
TZ = os.getenv("TZ_NAME", "Europe/Madrid")

GOOGLE_TOKEN = os.getenv("GOOGLE_TOKEN", "token.json")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ALLOWED_CHAT_IDS = {
    int(x) for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
}
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "")
