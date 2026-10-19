"""Local LLM via Ollama's HTTP API (replaces Gemini)."""
from __future__ import annotations

import json
import re
from typing import Callable

import requests

import config

# Small models sometimes write a tool call as text: Web_search({"query": "..."})
TEXT_CALL = re.compile(r"^\s*(\w+)\s*\(\s*(\{.*\})\s*\)\s*$", re.S)


class TokyoBrain:

  def __init__(self, tools: list | None = None,
               handlers: dict[str, Callable] | None = None):
    self.tools = tools or []
    self.handlers = handlers or {}

  def _chat(self, messages: list, use_tools: bool, **options) -> dict:
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "24h",  # keep the model in RAM, avoid slow reloads
        "options": {"temperature": 0.4, "num_ctx": 4096, **options},
    }
    if use_tools and self.tools:
      payload["tools"] = self.tools
    r = requests.post(f"{config.OLLAMA_URL}/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["message"]

  def _text_tool_call(self, content: str) -> dict | None:
    """Turn 'Web_search({...})' text into a real tool call, if it names a known tool."""
    m = TEXT_CALL.match(content or "")
    if not m:
      return None
    name = m.group(1).lower()
    if name not in self.handlers:
      return None
    try:
      return {"function": {"name": name, "arguments": json.loads(m.group(2))}}
    except json.JSONDecodeError:
      return None

  def rewrite_query(self, history: list, text: str) -> str:
    """'jam misa di gereja itu?' -> 'horario misas Nuestra Señora de la Merced Madrid'."""
    messages = [
        {"role": "system", "content": (
            "Rewrite the user's last message as a short web search query (max 8 words). "
            "Remove command words like search, cari, busca, tolong, please. "
            "Replace references like 'that church' with the actual name from the conversation. "
            "For places or services in Spain, write the query in Spanish; otherwise in English. "
            "Output ONLY the query, no quotes.")},
        *history[-4:],
        {"role": "user", "content": text},
    ]
    query = self._chat(messages, use_tools=False, temperature=0, num_predict=30)
    return (query.get("content") or text).strip().strip('"').splitlines()[0]

  def generate_response(self, system_prompt: str, history: list,
                        user_message: str, use_tools: bool = True) -> str:
    messages = [{"role": "system", "content": system_prompt},
                *history[-6:],  # small model, small memory: last 3 exchanges
                {"role": "user", "content": user_message}]
    msg = self._chat(messages, use_tools=use_tools)
    calls = msg.get("tool_calls") or []
    if not calls and use_tools:
      fake = self._text_tool_call(msg.get("content", ""))
      if fake:
        calls = [fake]
        msg = {"role": "assistant", "content": "", "tool_calls": calls}
    if not calls:
      return (msg.get("content") or "").strip()

    messages.append(msg)
    for call in calls:
      fn = call["function"]
      args = fn.get("arguments") or {}
      if isinstance(args, str):
        args = json.loads(args)
      handler = self.handlers.get(fn["name"].lower())
      try:
        result = handler(**args) if handler else f"Unknown tool {fn['name']}"
      except Exception as e:  # bad args from a small model shouldn't crash us
        result = f"Tool error: {e}"
      messages.append({"role": "tool", "tool_name": fn["name"],
                       "content": str(result)})
    return (self._chat(messages, use_tools=False).get("content") or "").strip()