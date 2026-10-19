#!/usr/bin/env bash
# Downloads Piper voices (~60 MB each) from Hugging Face.
set -euo pipefail
DIR="${1:-voices}"; mkdir -p "$DIR"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main"
for path in \
  id/id_ID/news_tts/medium/id_ID-news_tts-medium \
  en/en_US/lessac/medium/en_US-lessac-medium \
  es/es_ES/davefx/medium/es_ES-davefx-medium; do
  name="$(basename "$path")"
  for ext in onnx onnx.json; do
    [ -f "$DIR/$name.$ext" ] || curl -fsSL "$BASE/$path.$ext" -o "$DIR/$name.$ext"
  done
  echo "✓ $name"
done
