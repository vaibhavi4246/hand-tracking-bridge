"""
DashboardSink: bridges the pipeline into the FastAPI dashboard's WebSocket broadcast.

Calls broadcast_from_thread() from server.py on every frame so that browser
clients connected to /ws receive live gesture data.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from hand_tracking_bridge.sinks.base import OutputSink

if TYPE_CHECKING:
    from hand_tracking_bridge.gestures.types import GestureFrame


class DashboardSink(OutputSink):
    """Forwards each GestureFrame to the dashboard's WebSocket broadcast."""

    def open(self) -> None:
        pass  # Server is started separately in cli.py

    def send(self, frame: "GestureFrame") -> None:
        from hand_tracking_bridge.dashboard.server import broadcast_from_thread
        broadcast_from_thread(json.dumps(frame.to_dict()))

    def close(self) -> None:
        pass

    def __repr__(self) -> str:
        return "DashboardSink()"
