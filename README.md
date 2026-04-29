# SmartFeed News Automation

Full-stack monorepo for automated RSS ingestion, random platform assignment, media generation, mock publishing, Telegram notifications, and dashboard operations.

## Project Structure

```text
project-root/
|
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- routes/
|   |   |-- services/
|   |   |-- models/
|   |   |-- utils/
|   |   `-- config.py
|   |-- requirements.txt
|   `-- Dockerfile
|
|-- frontend/
|   |-- src/
|   |-- public/
|   |-- index.html
|   |-- package.json
|   `-- vite.config.js
|
|-- n8n/
|   `-- workflow.json
|
|-- database/
|   `-- mongo-init.js
|
|-- assets/
|   |-- templates/
|   |-- fonts/
|   `-- audio/
|
|-- .env.example
|-- docker-compose.yml
`-- README.md
```

## Features Implemented

- RSS fetch from tamil, english, sports feeds
- Deduplication in MongoDB via unique `rss_id`
- Random assignment to one platform only (`instagram` or `youtube`)
- Instagram media generator (1080x1080 image with title overlay)
- YouTube Shorts generator (1080x1920 video from image + optional audio)
- Mock upload services for both platforms
- Telegram notification on successful upload
- Error propagation when upload fails
- Dashboard with filters, status cards, retry and generate controls
- n8n workflow that runs every 30 minutes

## Backend API

- `GET /posts`
- `POST /process-rss`
- `POST /generate/`
  - With body `{ "rss_id": "..." }` for single item
  - With body `{ "limit": 10 }` for queued batch
- `POST /retry/`
  - With body `{ "rss_id": "..." }`
- `GET /headlines/random?limit=5`
  - Returns random queued/failed headlines for manual selection (limit clamped to 5..10)
- `POST /upload-selected/`
  - With body `{ "rss_ids": ["..."], "platform": "youtube" | "instagram" }`

## Local Run (Without Docker)

## Quick Start Commands

From project root:

```bash
# Start only frontend
npm start

# Start backend with one command
npm run start:backend

# Start Mongo only (Docker)
npm run start:mongo
```

If you prefer Python command directly for backend:

```bash
cd backend
python start.py
```

### 1) Start MongoDB

Run local MongoDB on default port `27017`.

### 2) Backend setup

```bash
cd backend
python -m venv .venv
# bash (Git Bash / WSL)
source .venv/Scripts/activate
# Windows cmd
# .venv\Scripts\activate.bat
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Copy root `.env.example` to `.env` and update values.

For your current stage:

- Set `YOUTUBE_API_KEY` in `.env`
- Keep `INSTAGRAM_TOKEN` as placeholder for now

Start backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) Frontend setup

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Dashboard opens at `http://localhost:5173`.

## Website Flow For Manual Upload

1. Open dashboard in browser
2. Click `Fetch RSS`
3. Go to `Headline Picker`
4. Choose random count (5..10)
5. Click `Get Random Headlines`
6. Select headlines using checkboxes
7. Click `Upload Selected to YouTube` or `Upload Selected to Instagram`

This works directly from the website UI and posts through backend APIs.

## Important YouTube Note

Current project uses **mock upload functions** for both YouTube and Instagram.

- Your dashboard flow is real and complete end-to-end in this app.
- The final upload target URL is mocked.
- `YOUTUBE_API_KEY` alone is not enough for actual YouTube video upload; real upload requires OAuth 2.0 user authorization with upload scope.

If you want, the next step is integrating real YouTube Data API upload in place of the mock uploader.

## Docker Run (Optional)

```bash
docker compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- MongoDB: `mongodb://localhost:27017`

## n8n Workflow

Import `n8n/workflow.json` into n8n.

Workflow sequence:

1. Cron trigger every 30 minutes
2. HTTP POST to `/process-rss`
3. HTTP POST to `/generate/`
4. Telegram notify node with summary

Set up Telegram credentials in n8n before enabling workflow.

## Important Notes

- `assets/fonts/Montserrat-Regular.ttf` and `assets/audio/sample-audio.wav` are placeholders. Replace them with real files for production-quality output.
- If font loading fails, backend falls back to default Pillow font.
- FFmpeg must be installed and available in PATH for video generation.
