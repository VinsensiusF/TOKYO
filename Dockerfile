FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ scripts/
RUN bash scripts/download_voices.sh /app/voices
COPY . .
ENV VOICES_DIR=/app/voices PYTHONUNBUFFERED=1
