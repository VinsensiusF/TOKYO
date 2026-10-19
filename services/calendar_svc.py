"""Google Calendar: read all calendars (incl. subscribed campus ones) + add items.
Also owns the shared Google login (get_creds) used by Gmail."""
from __future__ import annotations

import datetime as dt
import os
import re
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import config

# One token for all Google services. Changing this list requires a new login.
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",  # read only: can't send/delete
]
MADRID = ZoneInfo(config.TZ)
IGNORE = ("last update",)  # sync markers from subscribed calendars, not real events

DAY_NAMES = {
    "id": ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
}
TAGS = {"id": ("HARI INI", "BESOK"), "en": ("TODAY", "TOMORROW"), "es": ("HOY", "MAÑANA")}
NO_EVENTS = {"id": "tidak ada acara", "en": "no events", "es": "sin eventos"}


# --- Google login (shared by Calendar + Gmail) ---

def get_creds() -> Credentials:
  creds = None
  if os.path.exists(config.GOOGLE_TOKEN):
    creds = Credentials.from_authorized_user_file(config.GOOGLE_TOKEN, SCOPES)

  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
      with open(config.GOOGLE_TOKEN, "w") as f:  # save the refreshed token
        f.write(creds.to_json())
    else:
      # No browser inside Docker: fail clearly instead of trying to open one.
      raise RuntimeError(
          f"{config.GOOGLE_TOKEN} missing or invalid. Run: "
          "docker compose run --rm -p 8765:8765 web python google_login.py")
  return creds


def get_calendar_service():
  return build("calendar", "v3", credentials=get_creds(), cache_discovery=False)


# --- Write ---

def add_deadline(title: str, due_date: str) -> str:
  try:
    day = dt.date.fromisoformat(due_date)  # rejects bad dates from the LLM
    event = {
        "summary": title,
        "description": "Added by TOKYO",
        "start": {"date": day.isoformat()},
        # All-day end date is exclusive: end == start makes Google reject it.
        "end": {"date": (day + dt.timedelta(days=1)).isoformat()},
    }
    get_calendar_service().events().insert(calendarId="primary", body=event).execute()
    return f"Added '{title}' on {day.isoformat()}."
  except Exception as e:
    return f"Failed to add agenda: {e}"


# --- Read ---

def _parse(t: dict) -> tuple[dt.datetime, bool]:
  """Google gives 'date' for all-day events, 'dateTime' for timed ones."""
  raw = t.get("dateTime", t.get("date"))
  if "T" not in raw:
    return dt.datetime.fromisoformat(raw).replace(tzinfo=MADRID), True
  return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(MADRID), False


def get_events(days_ahead: int = 7, limit: int = 40) -> list[dict]:
  """Events from every calendar, from the start of today, sorted, in Madrid time."""
  service = get_calendar_service()
  start_of_today = dt.datetime.now(MADRID).replace(hour=0, minute=0, second=0, microsecond=0)
  until = start_of_today + dt.timedelta(days=days_ahead)
  events = []
  for cal in service.calendarList().list().execute().get("items", []):
    try:
      items = service.events().list(
          calendarId=cal["id"], timeMin=start_of_today.isoformat(),
          timeMax=until.isoformat(), maxResults=limit,
          singleEvents=True, orderBy="startTime",
      ).execute().get("items", [])
    except Exception:
      continue
    for it in items:
      title = re.sub(r"\s+", " ", it.get("summary", "(no title)")).strip("* ")
      if any(word in title.lower() for word in IGNORE):
        continue
      start, all_day = _parse(it["start"])
      end, _ = _parse(it["end"])
      events.append({
          "summary": title,
          "start": start,
          "end": end,
          "all_day": all_day,
          "location": it.get("location", ""),
          "calendar": cal.get("summary", ""),
      })
  events.sort(key=lambda e: e["start"])
  return events[:limit]


# --- Format ---

def format_agenda(events: list[dict] | None, days: list[dt.date], lang: str) -> str:
  """Only the requested days, with headers already in the reply language,
  so the model copies instead of translating (where it mislabeled days)."""
  if events is None:
    return ("CALENDAR NOT CONNECTED. If asked about schedule, say the calendar "
            "connection failed. Never claim the user has no events.")
  lang = lang if lang in DAY_NAMES else "en"
  today = dt.datetime.now(MADRID).date()
  tags = {today: TAGS[lang][0], today + dt.timedelta(days=1): TAGS[lang][1]}
  lines = []
  for day in days:
    tag = f" ({tags[day]})" if day in tags else ""
    lines.append(f"{DAY_NAMES[lang][day.weekday()]} {day:%d/%m}{tag}:")
    todays = [e for e in events if e["start"].date() == day]
    if not todays:
      lines.append(f"  - {NO_EVENTS[lang]}")
    for e in todays:
      when = "all day" if e["all_day"] else f"{e['start']:%H:%M}-{e['end']:%H:%M}"
      # Campus titles often already contain the room: don't repeat it.
      where = f" @ {e['location']}" if e["location"] and e["location"] not in e["summary"] else ""
      lines.append(f"  - {when} {e['summary']}{where}")
  return "\n".join(lines)


def get_deadlines_list(events: list[dict]) -> str:
  """Markdown for the web sidebar."""
  if not events:
    return "Tidak ada agenda mendatang."
  return "\n".join(
      f"- **{e['summary']}**  \n  🕒 {e['start'].strftime('%a %d %b' if e['all_day'] else '%a %d %b, %H:%M')}"
      for e in events[:6])