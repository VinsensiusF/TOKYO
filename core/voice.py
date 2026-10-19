"""Local speech: faster-whisper (ears) + Piper (mouth). No cloud calls."""
from __future__ import annotations

import io
import os
import re
import subprocess
import wave
from functools import lru_cache

import config
from core.lang import LANGS

MAX_SPOKEN_CHARS = 1200  # long replies take long to synthesize on CPU


@lru_cache(maxsize=1)
def _whisper():
  from faster_whisper import WhisperModel  # lazy: load on first voice message

  return WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")


@lru_cache(maxsize=len(LANGS))
def _piper(voice_name: str):
  from piper import PiperVoice

  return PiperVoice.load(os.path.join(config.VOICES_DIR, f"{voice_name}.onnx"))


def transcribe(audio: bytes) -> tuple[str, str | None]:
  """Any format (Telegram ogg, browser wav). Returns (text, detected_lang)."""
  segments, info = _whisper().transcribe(
      io.BytesIO(audio), beam_size=1, vad_filter=True
  )
  text = " ".join(s.text.strip() for s in segments).strip()
  return text, info.language


def clean_for_speech(text: str) -> str:
  text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [label](url) -> label
  text = re.sub(r"[*_`#>|~]", "", text)
  text = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]", "", text)
  return re.sub(r"\s+", " ", text).strip()[:MAX_SPOKEN_CHARS]


def speak_wav(text: str, lang: str) -> bytes:
  voice = _piper(LANGS[lang][1])
  buf = io.BytesIO()
  with wave.open(buf, "wb") as wf:
    if hasattr(voice, "synthesize_wav"):  # piper-tts >= 1.3
      voice.synthesize_wav(clean_for_speech(text), wf)
    else:  # piper-tts 1.2
      voice.synthesize(clean_for_speech(text), wf)
  return buf.getvalue()


def wav_to_ogg(wav: bytes) -> bytes:
  """Telegram voice notes must be OGG/Opus, otherwise they arrive as files."""
  return subprocess.run(
      ["ffmpeg", "-loglevel", "error", "-i", "pipe:0",
       "-c:a", "libopus", "-b:a", "32k", "-f", "ogg", "pipe:1"],
      input=wav, capture_output=True, check=True,
  ).stdout
