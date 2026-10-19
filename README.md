# TOKYO — Tracks Obligations, Keeps You On-time

Local, private assistant: Qwen2.5 3B (Ollama) + faster-whisper + Piper.
Same brain, two doors: web app (Streamlit) and Telegram bot.

## Run locally (laptop)
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
bash scripts/download_voices.sh          # Piper voices -> ./voices
ollama pull qwen2.5:3b                   # install Ollama first: ollama.com
cp .env.example .env                     # fill in values
streamlit run main.py                    # web
python bot.py                            # telegram (second terminal)
```
Also needs `ffmpeg` (`brew install ffmpeg`) for Telegram voice notes.

## Run on laptop with Docker only
```bash
mkdir -p secrets && cp token.json credentials.json secrets/
cp .env.example .env
docker compose up -d --build            # no Caddy locally
docker compose exec ollama ollama pull qwen2.5:3b
open http://localhost:8501
```

## Google login (once, on your laptop)
The browser OAuth flow can't run on a headless VPS. Run the app locally once,
log in, then copy `token.json` + `credentials.json` into `secrets/` on the server.

## Deploy on VPS
```bash
mkdir secrets && cp token.json credentials.json secrets/
cp .env.example .env && nano .env        # set WEB_PASSWORD!
nano Caddyfile                           # your domain
docker compose --profile prod up -d --build
docker compose exec ollama ollama pull qwen2.5:3b
```
DNS: an A record `tokyo` -> VPS IP. Telegram works even without the domain.
