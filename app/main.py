"""FastAPI entrypoint: mounts the API + WebSocket and serves the built React app.

One process serves REST, the application WebSocket, and the compiled frontend
(per architecture.md — a single Azure Container App).
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import debug, documents, routes, voice, ws
from .config import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(title="Bank Alfa Mortgage AI Demo", version="0.1.0")

# Local dev: Vite runs on :5173 and talks to the API on :8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)
app.include_router(debug.router)
app.include_router(documents.router)
app.include_router(voice.router)
app.include_router(ws.router)

# Serve the compiled React build if present (production / container).
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str) -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")
