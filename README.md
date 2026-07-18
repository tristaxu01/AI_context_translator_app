# AI_context_translator_app

A FastAPI + React application for speech transcription and translation with optional background context.

## Features
- **Live translation mode** via WebSocket (`/ws/live`) for browser microphone transcription flows.
- **File upload translation mode** via synchronous HTTP (`/api/files/translate`) for audio/video files.
- Optional **background context** (for example, `technical interview` or `medical conference`) applied to both modes.
- **Settings dashboard** for target language, voice, and output mode (`text` or `audio`).
- Backend and frontend are containerized for deployment (for example, to Google Cloud Run).

## Backend
```bash
pip install -r backend/requirements-dev.txt
pytest -q
uvicorn backend.app.main:app --reload
```

## Frontend
```bash
cd frontend
npm install
npm run dev
```

## Docker
```bash
docker compose up --build
```
