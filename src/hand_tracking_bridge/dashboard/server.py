"""
FastAPI web dashboard server.

Serves a real-time hand tracking visualization at http://localhost:8000.
Streams gesture data to browser clients via WebSocket at /ws.

The WebSocketSink calls broadcast() from the pipeline thread via
asyncio's thread-safe call_soon_threadsafe().
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class ConnectionManager:
    """Manages active WebSocket connections for broadcast."""

    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.debug("Dashboard: client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.debug("Dashboard: client disconnected (%d total)", len(self.active))

    async def broadcast(self, message: str) -> None:
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.active:
                self.active.remove(ws)


# Global manager — shared between HTTP server and the pipeline's broadcast calls
manager = ConnectionManager()
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def broadcast_from_thread(payload: str) -> None:
    """
    Thread-safe: post a broadcast to the dashboard's asyncio event loop.
    Called by the pipeline's DispatcherThread when dashboard is enabled.
    """
    if _event_loop is None or not manager.active:
        return
    _event_loop.call_soon_threadsafe(
        lambda: asyncio.ensure_future(manager.broadcast(payload), loop=_event_loop)
    )


def create_app() -> "FastAPI":
    if not _FASTAPI_AVAILABLE:
        raise ImportError("Dashboard requires fastapi: pip install fastapi uvicorn")

    app = FastAPI(title="Hand Tracking Bridge Dashboard", version="2.0.0")

    @app.on_event("startup")
    async def _capture_loop() -> None:
        global _event_loop
        _event_loop = asyncio.get_event_loop()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html_path = STATIC_DIR / "index.html"
        if html_path.exists():
            return HTMLResponse(html_path.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Dashboard static files not found.</h1>")

    @app.get("/void", response_class=FileResponse)
    async def void_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "void.html", media_type="text/html")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "clients": len(manager.active)}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await manager.connect(ws)
        try:
            while True:
                # Keep connection alive — client sends pings
                await ws.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(ws)

    return app
