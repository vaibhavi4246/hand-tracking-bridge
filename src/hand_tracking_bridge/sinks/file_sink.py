"""
File output sink — records gesture data to JSON Lines format for later playback.

Each line in the output file is a complete GestureFrame serialized as JSON,
with a monotonic timestamp for timing-accurate replay.

Usage:
    sink = FileSink(Path("recordings/session.jsonl"))
    with sink:
        sink.send(frame)  # writes one line per frame

Replay:
    hand-tracker --playback recordings/session.jsonl
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Optional

from hand_tracking_bridge.gestures.types import GestureFrame
from hand_tracking_bridge.sinks.base import OutputSink

logger = logging.getLogger(__name__)


class FileSink(OutputSink):
    """
    Writes gesture frames to a JSON Lines (.jsonl) file.
    Thread-safe: uses a threading.Lock around file writes.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._file = None
        self._lock = threading.Lock()
        self._frame_count = 0

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "w", encoding="utf-8", buffering=1)
        logger.info("FileSink: recording to %s", self.path)

    def send(self, frame: GestureFrame) -> None:
        if self._file is None:
            return
        line = json.dumps(frame.to_dict()) + "\n"
        with self._lock:
            self._file.write(line)
            self._frame_count += 1

    def close(self) -> None:
        if self._file is not None:
            with self._lock:
                self._file.flush()
                self._file.close()
                self._file = None
        logger.info("FileSink: recorded %d frames to %s", self._frame_count, self.path)

    def __repr__(self) -> str:
        return f"FileSink(path={self.path!r})"
