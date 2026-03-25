"""
DispatcherThread: Routes GestureFrames to all registered output sinks.

Fault isolation: a failure in one sink does not affect others.
Each sink's exception is logged and the dispatcher continues running.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import List

from hand_tracking_bridge.gestures.types import GestureFrame
from hand_tracking_bridge.sinks.base import OutputSink

logger = logging.getLogger(__name__)


class DispatcherThread(threading.Thread):
    """
    Pulls GestureFrames from gesture_queue and fans out to all sinks.
    """

    def __init__(
        self,
        gesture_queue: queue.Queue,
        sinks: List[OutputSink],
        shutdown: threading.Event,
    ) -> None:
        super().__init__(name="DispatcherThread", daemon=True)
        self.gesture_queue = gesture_queue
        self.sinks = sinks
        self.shutdown = shutdown
        self._frames_dispatched = 0

    def run(self) -> None:
        logger.info("DispatcherThread: started with %d sinks: %s", len(self.sinks), self.sinks)

        while not self.shutdown.is_set():
            try:
                frame: GestureFrame = self.gesture_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            for sink in self.sinks:
                try:
                    sink.send(frame)
                except Exception as exc:
                    logger.warning("DispatcherThread: sink %s error: %s", sink, exc)

            self._frames_dispatched += 1

        # Drain remaining frames on shutdown
        while True:
            try:
                frame = self.gesture_queue.get_nowait()
                for sink in self.sinks:
                    try:
                        sink.send(frame)
                    except Exception:
                        pass
            except queue.Empty:
                break

        logger.info("DispatcherThread: stopped. dispatched=%d", self._frames_dispatched)
