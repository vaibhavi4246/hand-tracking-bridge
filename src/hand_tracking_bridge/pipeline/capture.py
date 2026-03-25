"""
CaptureThread: Webcam producer.

Reads frames from the camera at the target FPS and places them on a
bounded queue. When the queue is full (inference is too slow), the
oldest frame is dropped — keeping system latency bounded rather than
letting a backlog of stale frames accumulate.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

from hand_tracking_bridge.config import CaptureConfig

logger = logging.getLogger(__name__)


@dataclass
class CaptureStats:
    frames_captured: int = 0
    frames_dropped: int = 0
    _fps_timestamps: list = field(default_factory=list)

    @property
    def actual_fps(self) -> float:
        now = time.monotonic()
        self._fps_timestamps = [t for t in self._fps_timestamps if now - t < 2.0]
        return len(self._fps_timestamps) / 2.0 if self._fps_timestamps else 0.0

    def record_frame(self) -> None:
        self.frames_captured += 1
        self._fps_timestamps.append(time.monotonic())


class CaptureThread(threading.Thread):
    """
    Reads webcam frames and puts (timestamp, frame) tuples on frame_queue.

    Queue design: maxsize=2 means at most 2 unprocessed frames wait at any time.
    If the queue is full when a new frame arrives, the new frame is dropped
    (not the old ones — we prefer recency over completeness).
    """

    def __init__(
        self,
        frame_queue: queue.Queue,
        shutdown: threading.Event,
        config: CaptureConfig,
    ) -> None:
        super().__init__(name="CaptureThread", daemon=True)
        self.frame_queue = frame_queue
        self.shutdown = shutdown
        self.config = config
        self.stats = CaptureStats()
        self._cap: cv2.VideoCapture | None = None

    def run(self) -> None:
        self._cap = cv2.VideoCapture(self.config.camera_index)
        if not self._cap.isOpened():
            logger.error("CaptureThread: cannot open camera index %d", self.config.camera_index)
            self.shutdown.set()
            return

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.config.target_fps)

        frame_interval = 1.0 / self.config.target_fps
        logger.info(
            "CaptureThread: opened camera %d at %dx%d @ %dfps",
            self.config.camera_index,
            self.config.width,
            self.config.height,
            self.config.target_fps,
        )

        while not self.shutdown.is_set():
            loop_start = time.monotonic()
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("CaptureThread: frame read failed, retrying...")
                time.sleep(0.05)
                continue

            captured_at = time.monotonic()
            self.stats.record_frame()

            # Mirror horizontally for natural interaction
            frame = cv2.flip(frame, 1)

            try:
                self.frame_queue.put_nowait((captured_at, frame))
            except queue.Full:
                self.stats.frames_dropped += 1

            # Throttle to target FPS
            elapsed = time.monotonic() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        if self._cap is not None:
            self._cap.release()
        logger.info(
            "CaptureThread: stopped. captured=%d dropped=%d",
            self.stats.frames_captured,
            self.stats.frames_dropped,
        )
