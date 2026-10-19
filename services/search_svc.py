"""Free web search via DuckDuckGo + reads the top pages (no API key).

Snippets alone rarely contain the answer (mass times, opening hours),
so the top results are opened and only the relevant sentences are kept."""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urlparse

import requests

from concurrent.futures import ThreadPoolExecutor

# Ads, redirects and ticket resellers: often wrong or outdated hours.
JUNK = ("bing.com", "duckduckgo.com", "google.com", "tiqets", "getyourguide",
        "viator", "civitatis", "booking.com", "tripadvisor")
TIME = re.compile(r"\b\d{1,2}[:.h]\d{2}\b|\b\d{1,2}\s?(am|pm|h)\b", re.I)
SEASON_HEAD = re.compile(
    r"horario\s+de\s+(verano|invierno)|\b(summer|winter)\s+(hours|schedule|timetable)", re.I)
UA = {"User-Agent": "Mozilla/5.0 (TOKYO personal assistant)"}


def _domain(url: str) -> str:
  return urlparse(url).netloc.removeprefix("www.")


def _current_season() -> str | None:
  """Spanish parishes/museums usually switch to summer hours in July-August."""
  month = dt.date.today().month
  if month in (7, 8):
    return "summer"
  if month in (6, 9):
    return None  # transition months: keep both, let the user see both
  return "winter"


def _kind(match: re.Match) -> str:
  w = match.group(0).lower()
  return "summer" if ("verano" in w or "summer" in w) else "winter"


def _keep_current_season(text: str) -> str:
  """If a page has both a summer and a winter table, drop the one not in force,
  so the small model can't mix them."""
  season = _current_season()
  heads = list(SEASON_HEAD.finditer(text))
  if season is None or len({_kind(h) for h in heads}) < 2:
    return text
  parts = [text[:heads[0].start()]]  # intro (name, address)
  for i, h in enumerate(heads):
    end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
    if _kind(h) == season:
      parts.append(text[h.start():end])
  return "".join(parts)


def _page_text(url: str) -> str:
  try:
    import trafilatura

    html = requests.get(url, headers=UA, timeout=6).text
    return _keep_current_season(trafilatura.extract(html) or "")
  except Exception:
    return ""  # blocked, slow or broken page: just skip it


def _relevant(text: str, query: str, limit: int = 1000) -> str:
  """Keep the sentences that mention the query words or contain times."""
  words = {w for w in re.findall(r"\w{4,}", query.lower())}
  sentences = re.split(r"(?<=[.!?\n])\s+", text)
  scored = [(sum(w in s.lower() for w in words) + 2 * len(TIME.findall(s)), i, s)
            for i, s in enumerate(sentences) if s.strip()]
  best = sorted(scored, reverse=True)[:12]
  out, size = [], 0
  for score, _, s in sorted(best, key=lambda t: t[1]):  # back to page order
    if score == 0 or size + len(s) > limit:
      continue
    out.append(s.strip())
    size += len(s)
  return " ".join(out)


def web_search(query: str, n: int = 8, candidates: int = 3) -> str:
  """Opens the top pages in parallel and keeps ONE: the page with the most
  concrete times/facts. One source = nothing for a small model to mix up."""
  try:
    from ddgs import DDGS

    raw = DDGS().text(query, max_results=n)
  except Exception as e:  # DDG rate-limits sometimes: report, don't crash
    return f"Search failed: {e}"

  results, seen = [], set()
  for r in raw or []:
    d = _domain(r.get("href", ""))
    if not d or d in seen or any(j in d for j in JUNK):
      continue
    seen.add(d)
    results.append({**r, "domain": d})
  if not results:
    return "No results."

  top = results[:candidates]
  with ThreadPoolExecutor(max_workers=candidates) as pool:  # ~6s total, not 18s
    excerpts = list(pool.map(lambda r: _relevant(_page_text(r["href"]), query), top))

  pages = [(len(TIME.findall(ex)) + len(ex) / 1000, r["domain"], ex)
           for r, ex in zip(top, excerpts) if ex]
  if pages:
    _, domain, excerpt = max(pages)
    return f"SOURCE: {domain}\n{excerpt}"

  # No page readable: fall back to snippets from the best few results.
  return "\n".join(f"- ({r['domain']}) {r.get('title', '')}: {r.get('body', '')}"
                   for r in results[:3])