"""The one kitchen both serving windows (web + Telegram) order from."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from core import context
from core.brain import TokyoBrain
from core.dates import days_asked, is_schedule_question
from core.intents import is_email_question, strip_intent, wants_search
from core.lang import detect_text, normalize
from core.voice import speak_wav, transcribe
from services.calendar_svc import add_deadline, format_agenda
from services.gmail_svc import format_emails, get_recent_emails
from services.search_svc import web_search

NOT_HEARD = {
    "id": "Maaf, suaramu nggak kedengeran. Coba lagi?",
    "en": "Sorry, I couldn't hear that. Try again?",
    "es": "Perdona, no te he oído bien. ¿Otra vez?",
}
SCHEDULE_INTRO = {"id": "📅 Jadwalmu:", "en": "📅 Your schedule:", "es": "📅 Tu horario:"}

TOOLS = [
    {"type": "function", "function": {
        "name": "add_deadline",
        "description": "Add an all-day agenda item or deadline to the user's Google Calendar.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"},
            "due_date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["title", "due_date"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the internet for facts you don't know: places, opening hours, news, prices.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Short search query"}},
            "required": ["query"]}}},
]


def _add_deadline(title: str, due_date: str) -> str:
  result = add_deadline(title, due_date)
  context.invalidate("agenda")  # next answer sees the new event
  return result


brain = TokyoBrain(TOOLS, {"add_deadline": _add_deadline, "web_search": web_search})


@dataclass
class Reply:
  text: str
  lang: str
  heard: str | None = None  # transcript, for voice input


def _llm(text: str, history: list, lang: str, extra: str = "", tools: bool = True) -> str:
  prompt = context.build_system_prompt(lang, text, extra)
  return brain.generate_response(prompt, history, text, use_tools=tools)


def _search(text: str, history: list) -> tuple[str, str]:
  """LLM writes the query; if that finds nothing, retry with a code-cleaned query."""
  query = brain.rewrite_query(history, text)
  results = web_search(query)
  if results.startswith(("Search failed", "No results")):
    time.sleep(1)  # DDG dislikes rapid repeats
    query = strip_intent(text)
    results = web_search(query)
  logging.info("Web search: %s", query)
  return query, results


def _answer(text: str, history: list, lang: str) -> str:
  """Code routes by intent; the LLM only writes the final answer.
  Order matters: explicit 'search' beats 'jadwal' ("cari jadwal misa...")."""
  if is_email_question(text):
    try:
      emails = format_emails(get_recent_emails())
    except Exception as e:  # no Gmail permission yet, token expired...
      logging.warning("Gmail unavailable: %s", e)
      emails = "GMAIL NOT CONNECTED. Tell the user the Gmail connection failed."
    return _llm(text, history, lang, f"\nEMAILS (last 2 days):\n{emails}\n", tools=False)

  if wants_search(text):
    query, results = _search(text, history)
    return _llm(text, history, lang, f"\nWEB RESULTS for '{query}':\n{results}\n", tools=False)

  events = context.events()
  if events is not None and is_schedule_question(text):
    return f"{SCHEDULE_INTRO[lang]}\n{format_agenda(events, days_asked(text), lang)}"

  return _llm(text, history, lang)


def ask_text(text: str, history: list, last_lang: str) -> Reply:
  lang = detect_text(text, last_lang)
  return Reply(_answer(text, history, lang), lang)


def ask_voice(audio: bytes, history: list, last_lang: str) -> Reply:
  heard, whisper_lang = transcribe(audio)
  if not heard:
    return Reply(NOT_HEARD[last_lang], last_lang, "")
  # Whisper hears the accent, so trust it first; fall back to text detection.
  lang = normalize(whisper_lang, detect_text(heard, last_lang))
  return Reply(_answer(heard, history, lang), lang, heard)


def speak(reply: Reply) -> bytes:
  return speak_wav(reply.text, reply.lang)