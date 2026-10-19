"""Language detection + the language -> Piper voice map.

To add a language: add it to LANGS, give it a few STOPWORDS,
and add its voice to scripts/download_voices.sh.
"""
from __future__ import annotations

import re
import unicodedata

from langdetect import DetectorFactory, detect_langs

DetectorFactory.seed = 0  # langdetect is random by default; make it repeatable

LANGS = {
    "id": ("Indonesian", "id_ID-news_tts-medium"),
    "en": ("English", "en_US-lessac-medium"),
    "es": ("Spanish", "es_ES-davefx-medium"),
}
# Close relatives that detectors confuse with a supported language.
ALIASES = {"ms": "id", "jw": "id", "su": "id", "ca": "es", "gl": "es"}

# Frequent words that are distinctive per language (accents stripped).
STOPWORDS = {
    "id": {"aku", "saya", "kamu", "apa", "ada", "yang", "ini", "itu", "dan", "di",
           "ke", "besok", "hari", "kelas", "jadwal", "gimana", "nggak", "gak",
           "tolong", "dong", "aja", "sama", "buat", "harus", "pakai", "cuaca"},
    "en": {"what", "do", "i", "have", "the", "my", "is", "are", "on", "today",
           "tomorrow", "how", "should", "wear", "please", "any", "class", "classes",
           "schedule", "weather", "you", "can", "will"},
    "es": {"que", "tengo", "el", "la", "los", "las", "mi", "mis", "hoy", "manana",
           "como", "es", "hay", "clase", "clases", "por", "favor", "tiempo", "y",
           "un", "una", "del", "esta", "semana", "debo", "ponerme", "puedes"},
}


def normalize(code: str | None, fallback: str) -> str:
  code = ALIASES.get(code or "", code)
  return code if code in LANGS else fallback


def _words(text: str) -> list[str]:
  t = unicodedata.normalize("NFKD", text.lower())
  t = "".join(c for c in t if not unicodedata.combining(c))
  return re.findall(r"[a-z]+", t)


def detect_text(text: str, fallback: str) -> str:
  """Stopword vote first (reliable on short questions), langdetect as tie-breaker.
  Tiny messages ("ok", "thx") keep the last language."""
  words = _words(text)
  scores = {lang: sum(w in sw for w in words) for lang, sw in STOPWORDS.items()}
  ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
  if ranked[0][1] >= 1 and ranked[0][1] > ranked[1][1]:
    return ranked[0][0]

  if len(text.strip()) < 12:
    return fallback
  try:
    best = detect_langs(text)[0]
  except Exception:
    return fallback
  return normalize(best.lang, fallback) if best.prob >= 0.8 else fallback


def name(code: str) -> str:
  return LANGS[code][0]