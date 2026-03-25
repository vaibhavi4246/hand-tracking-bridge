"""
WebSocket output sink — broadcasts gesture data as JSON to all connected browser clients.

Bridges the synchronous pipeline thread to an asyncio WebSocket server
using loop.call_soon_threadsafe().
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Optional, Set

try:
    import websockets
    from websockets.legacy.server import WebSocketServerProtocol
    _WEBSOCKETS_AVAILABLE = True
except ImportError:
    _WEBSOCKETS_AVAILABLE = False

from hand_tracking_bridge.gestures.types import GestureFrame
from hand_tracking_bridge.sinks.base import OutputSink

logger = logging.getLogger(__name__)


class WebSocketSink(OutputSink):
    """
    Runs a WebSocket server in a background thread.
    Broadcasts every GestureFrame as a JSON payload to all connected clients.

    Example client JS:
        const ws = new WebSocket("ws://localhost:8765");
        ws.onmessage = (e) => { const frame = JSON.parse(e.data); ... };
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        if not _WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package required: pip install websockets")
        self.host = host
        self.port = port
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._clients: Set = set()
        self._ready = threading.Event()

    def open(self) -> None:
        self._thread = threading.Thread(
            target=self._run_server, name="WebSocketSink", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("WebSocketSink: server failed to start within 5s")
        logger.info("WebSocketSink: listening on ws://%s:%d", self.host, self.port)

    def _run_server(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self) -> None:
        async def handler(ws: "WebSocketServerProtocol", path: str) -> None:
            self._clients.add(ws)
            logger.debug("WebSocketSink: client connected (%d total)", len(self._clients))
            try:
                await ws.wait_closed()
            finally:
                self._clients.discard(ws)
                logger.debug("WebSocketSink: client disconnected (%d total)", len(self._clients))

        async with websockets.serve(handler, self.host, self.port):
            self._ready.set()
            await asyncio.Future()  # Run forever until loop is stopped

    def send(self, frame: GestureFrame) -> None:
        """Thread-safe: posts broadcast to the asyncio event loop."""
        if self._loop is None or not self._clients:
            return
        payload = json.dumps(frame.to_dict())
        self._loop.call_soon_threadsafe(
            lambda: asyncio.ensure_future(self._broadcast(payload), loop=self._loop)
        )

    async def _broadcast(self, payload: str) -> None:
        if not self._clients:
            return
        dead = set()
        for ws in list(self._clients):
            try:
                await ws.send(payload)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    def close(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        logger.info("WebSocketSink: closed")

    def __repr__(self) -> str:
        return f"WebSocketSink(host={self.host!r}, port={self.port})"
