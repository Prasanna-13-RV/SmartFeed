FROM python:3.11-slim

WORKDIR /app

# System deps: ffmpeg for video + Liberation fonts for image text rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        fonts-liberation \
        fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Create persistent-mountable directories
RUN mkdir -p /data/generated/images /data/generated/videos

EXPOSE 8000

# Render injects $PORT — use shell form so the variable is expanded
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
