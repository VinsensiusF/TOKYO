"""Madrid weather via Open-Meteo (free, no API key).

Returns raw numbers only: the LLM writes the outfit advice in the user's language,
instead of a hard-coded Indonesian sentence.
"""
from __future__ import annotations

import requests

URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=40.4168&longitude=-3.7038"
    "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
    "&timezone=Europe%2FMadrid&forecast_days=1"
)

WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
       45: "fog", 48: "fog", 51: "drizzle", 53: "drizzle", 55: "drizzle",
       61: "rain", 63: "rain", 65: "heavy rain", 71: "snow", 73: "snow",
       75: "heavy snow", 80: "showers", 81: "showers", 82: "heavy showers",
       95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm"}


def get_madrid_weather() -> dict | None:
  try:
    d = requests.get(URL, timeout=5).json()
    cur, day = d["current"], d["daily"]
    return {
        "temperature": cur["temperature_2m"],
        "feels_like": cur["apparent_temperature"],
        "condition": WMO.get(cur["weather_code"], "unknown"),
        "wind_kmh": cur["wind_speed_10m"],
        "min": day["temperature_2m_min"][0],
        "max": day["temperature_2m_max"][0],
        "rain_chance": day["precipitation_probability_max"][0],
    }
  except Exception:
    return None


def weather_text(w: dict | None) -> str:
  if not w:
    return "(weather unavailable)"
  return (f"Now {w['temperature']}°C (feels {w['feels_like']}°C), {w['condition']}, "
          f"wind {w['wind_kmh']} km/h. Today {w['min']}–{w['max']}°C, "
          f"rain chance {w['rain_chance']}%.")
