"""Works out which days a schedule question is about (id/en/es).
Code does this instead of the 3B model, which mislabels days."""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from zoneinfo import ZoneInfo

import config

WEEKDAYS = [  # index = Python weekday(), Monday = 0
    ("senin", "monday", "lunes"),
    ("selasa", "tuesday", "martes"),
    ("rabu", "wednesday", "miercoles"),
    ("kamis", "thursday", "jueves"),
    ("jumat", "friday", "viernes"),
    ("sabtu", "saturday", "sabado"),
    ("hari minggu", "sunday", "domingo"),  # bare "minggu" also means "week"
]
# Longest phrases first: "pasado manana" must win over "manana".
RELATIVE = [
    (("lusa", "day after tomorrow", "pasado manana"), 2),
    (("hari ini", "today", "tonight", "malam ini", "hoy",
      "esta noche", "esta manana", "esta tarde"), 0),
    (("besok", "tomorrow", "manana"), 1),
]
WEEK = ("minggu ini", "pekan ini", "seminggu", "this week", "esta semana")


def _norm(text: str) -> str:
  """Lowercase and strip accents, so 'mañana' and 'manana' both match."""
  t = unicodedata.normalize("NFKD", text.lower())
  return "".join(c for c in t if not unicodedata.combining(c))


def _find(text: str, phrase: str) -> bool:
  return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def days_asked(text: str, span: int = 7) -> list[dt.date]:
  t = _norm(text)
  today = dt.datetime.now(ZoneInfo(config.TZ)).date()
  week = [today + dt.timedelta(days=i) for i in range(span)]
  if any(_find(t, p) for p in WEEK):
    return week

  offsets = set()
  for phrases, offset in RELATIVE:
    for p in phrases:
      if _find(t, p):
        offsets.add(offset)
        t = re.sub(rf"\b{re.escape(p)}\b", " ", t)  # don't match it twice
  for wd, names in enumerate(WEEKDAYS):
    if any(_find(t, n) for n in names):
      offsets.add((wd - today.weekday()) % 7)  # next occurrence, today included

  # No specific day mentioned (e.g. "any deadlines?"): give the whole week.
  return sorted(today + dt.timedelta(days=o) for o in offsets) if offsets else week

SCHEDULE = ("jadwal", "kelas", "kuliah", "agenda", "acara", "ada apa",
            "schedule", "class", "classes", "calendar", "lecture", "what do i have",
            "horario", "clase", "clases", "calendario", "que tengo")
# "Add an agenda item" contains "agenda" too, but must go to the LLM tool call.
ADD = ("tambah", "tambahkan", "simpan", "catat", "ingatkan",
       "add", "save", "remind", "agrega", "anade", "guarda", "apunta")


def is_schedule_question(text: str) -> bool:
  t = _norm(text)
  if any(_find(t, p) for p in ADD):
    return False
  return any(_find(t, p) for p in SCHEDULE)