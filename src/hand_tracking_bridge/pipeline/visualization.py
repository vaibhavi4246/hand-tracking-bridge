"""
Visualization: Main-thread OpenCV window renderer.

OpenCV's imshow() must be called from the main thread on Windows and macOS.
This module provides a thin render() function driven by the main thread loop,
reading annotated frames from viz_queue.
"""
from __future__ import annotations

import queue
import time
from collections import deque
from typing import Optional

import cv2
import numpy as np


class Visualizer:
    """
    Reads annotated frames from viz_queue and displays them via cv2.imshow.
    Must be called from the main thread.
    """

    def __init__(self, viz_queue: queue.Queue, title: str = "Hand Tracking Bridge") -> None:
        self.viz_queue = viz_queue
        self.title = title
        self._fps_buf: deque = deque(maxlen=30)
        self._last_frame: Optional[np.ndarray] = None

    def render(self) -> bool:
        """
        Pull the latest frame from viz_queue and display it.
        Returns False if 'q' is pressed or window is closed.
        Non-blocking: if queue is empty, re-renders last frame.
        """
        try:
            frame = self.viz_queue.get_nowait()
            self._last_frame = frame
        except queue.Empty:
            frame = self._last_frame

        if frame is not None:
            self._fps_buf.append(time.monotonic())
            fps = self._calculate_fps()
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (frame.shape[1] - 120, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 200, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(self.title, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return False
        # Only check window visibility after imshow has been called at least once;
        # getWindowProperty returns -1 on a non-existent window, which would
        # otherwise cause an immediate exit before the first frame arrives.
        if self._last_frame is not None:
            if cv2.getWindowProperty(self.title, cv2.WND_PROP_VISIBLE) < 1:
                return False
        return True

    def _calculate_fps(self) -> float:
        if len(self._fps_buf) < 2:
            return 0.0
        elapsed = self._fps_buf[-1] - self._fps_buf[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._fps_buf) - 1) / elapsed

    def close(self) -> None:
        cv2.destroyAllWindows()
