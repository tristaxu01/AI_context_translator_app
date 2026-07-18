from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class Settings(BaseModel):
    target_language: str = Field(default="Spanish", min_length=2)
    voice: str = Field(default="alloy", min_length=2)
    output_mode: Literal["text", "audio"] = "text"


class LiveMessage(BaseModel):
    transcript: str = Field(min_length=1)
    target_language: str = Field(default="Spanish", min_length=2)
    background_context: str | None = None
    voice: str = Field(default="alloy", min_length=2)
    output_mode: Literal["text", "audio"] = "text"


class TranslationResult(BaseModel):
    transcript: str
    translation: str
    target_language: str
    background_context: str | None = None
    output_mode: Literal["text", "audio"]
    audio_base64: str | None = None


class TranslationService:
    @staticmethod
    def _normalize_context(background_context: str | None) -> str:
        return background_context.strip() if background_context else ""

    def translate(self, text: str, target_language: str, background_context: str | None) -> str:
        context = self._normalize_context(background_context)
        prefix = f"[{target_language}]"
        if context:
            return f"{prefix} ({context}) {text}"
        return f"{prefix} {text}"

    def synthesize(self, text: str, voice: str) -> str:
        payload = f"voice={voice}|{text}".encode("utf-8")
        return base64.b64encode(payload).decode("ascii")

    def stream_chunks(self, translation: str) -> list[str]:
        words = translation.split()
        if not words:
            return []
        chunks: list[str] = []
        current: list[str] = []
        for word in words:
            current.append(word)
            if len(current) == 4:
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))
        return chunks


app = FastAPI(title="AI Context Translator API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

translation_service = TranslationService()
settings_state = Settings()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/settings", response_model=Settings)
def get_settings() -> Settings:
    return settings_state


@app.put("/api/settings", response_model=Settings)
def update_settings(payload: Settings) -> Settings:
    global settings_state
    settings_state = payload
    return settings_state


@app.post("/api/files/translate", response_model=TranslationResult)
async def translate_file(
    file: UploadFile = File(...),
    target_language: str = Form("Spanish"),
    background_context: str | None = Form(None),
    voice: str = Form("alloy"),
    output_mode: Literal["text", "audio"] = Form("text"),
) -> TranslationResult:
    content = await file.read()

    storage_dir = Path(os.getenv("STORAGE_DIR", "/tmp/cloud_storage"))
    storage_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "upload").suffix
    storage_path = storage_dir / f"{uuid4().hex}{ext}"
    storage_path.write_bytes(content)

    transcript = f"Transcribed {file.filename or 'upload'} ({len(content)} bytes)"
    translation = translation_service.translate(transcript, target_language, background_context)

    audio_base64 = None
    if output_mode == "audio":
        audio_base64 = translation_service.synthesize(translation, voice)

    return TranslationResult(
        transcript=transcript,
        translation=translation,
        target_language=target_language,
        background_context=background_context,
        output_mode=output_mode,
        audio_base64=audio_base64,
    )


@app.websocket("/ws/live")
async def live_translation_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            data = LiveMessage.model_validate(json.loads(raw))
            translation = translation_service.translate(
                data.transcript,
                data.target_language,
                data.background_context,
            )
            chunks = translation_service.stream_chunks(translation)
            for chunk in chunks:
                await websocket.send_json({"type": "translation_chunk", "content": chunk})

            payload = {
                "type": "translation_complete",
                "transcript": data.transcript,
                "translation": translation,
                "target_language": data.target_language,
                "background_context": data.background_context,
                "output_mode": data.output_mode,
            }
            if data.output_mode == "audio":
                payload["audio_base64"] = translation_service.synthesize(translation, data.voice)

            await websocket.send_json(payload)
    except (WebSocketDisconnect, json.JSONDecodeError, ValueError):
        return
