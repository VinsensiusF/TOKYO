"""Keyword intent routing (id/en/es). Code decides; the 3B model only writes."""
from __future__ import annotations

import re

from core.dates import _norm

EMAIL = ("email", "e-mail", "mail", "gmail", "inbox", "surel", "correo")
SEARCH = ("cari", "search", "google", "look up", "find out", "busca",
          "internet", "online", "berita", "news", "noticia")


def _starts(text: str, prefixes: tuple[str, ...]) -> bool:
  """Prefix match on word start: 'email' matches 'emailku', 'cari' matches 'carikan'."""
  return any(re.search(rf"\b{re.escape(p)}", text) for p in prefixes)


def is_email_question(text: str) -> bool:
  return _starts(_norm(text), EMAIL)


def wants_search(text: str) -> bool:
  return _starts(_norm(text), SEARCH)

FILLER = ("tolong", "dong", "please", "can you", "could you", "bisa", "kakak",
          "aku", "saya", "informasi", "info", "mengenai", "tentang")

def strip_intent(text: str) -> str:
  """'Cari jadwal misa di X' -> 'jadwal misa di X': a cleaner fallback query."""
  t = text
  for p in SEARCH + FILLER:
    t = re.sub(rf"\b{re.escape(p)}\w*", " ", t, flags=re.I)
  return re.sub(r"\s+", " ", t).strip(" ?.!¿¡,")