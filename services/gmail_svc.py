"""Read-only Gmail: newest inbox mails, Gmail-'important' ones first."""
from __future__ import annotations

import html
import re

from googleapiclient.discovery import build

from services.calendar_svc import get_creds


def get_recent_emails(
    query: str = "in:inbox newer_than:2d -category:promotions -category:social",
    limit: int = 8) -> list[dict]:
  svc = build("gmail", "v1", credentials=get_creds(), cache_discovery=False)
  ids = svc.users().messages().list(userId="me", q=query, maxResults=limit).execute()
  emails = []
  for m in ids.get("messages", []):
    msg = svc.users().messages().get(
        userId="me", id=m["id"], format="metadata",
        metadataHeaders=["From", "Subject"]).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    labels = msg.get("labelIds", [])
    emails.append({
        "from": re.sub(r"\s*<.*?>", "", headers.get("From", "")).strip('" '),
        "subject": headers.get("Subject", "(no subject)"),
        "snippet": html.unescape(msg.get("snippet", ""))[:220],
        "important": "IMPORTANT" in labels,
        "unread": "UNREAD" in labels,
    })
  emails.sort(key=lambda e: (not e["important"], not e["unread"]))
  return emails


def format_emails(emails: list[dict]) -> str:
  if not emails:
    return "(no emails in the last 2 days)"
  lines = []
  for e in emails:
    tags = " ".join(t for t, on in (("[IMPORTANT]", e["important"]), ("[UNREAD]", e["unread"])) if on)
    lines.append(f"- {tags} From {e['from']}: \"{e['subject']}\" — {e['snippet']}")
  return "\n".join(lines)