"""
PlaybackThread: Replay recorded gesture sessions without a webcam.

Reads a JSONL recording produced by FileSink and re-publishes GestureFrame
objects to the gesture_queue at the original recorded cadence.

Usage:
    hand-tracker --playback recordings/session.jsonl
    hand-tracker --playback recordings/session.jsonl --speed 0.5  # slow motion
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from hand_tracking_bridge.gestures.types import (
    FingerState,
    GestureFrame,
    GestureResult,
    absent_gesture,
)

logger = logging.getLogger(__name__)


def _deserialize_finger(d: dict) -> FingerState:
    return FingerState(
        name=d["name"],
        flexion=d["flexion"],
        tip_x=d["tip_x"],
        tip_y=d["tip_y"],
        tip_z=d.get("tip_z", 0.0),
    )


def _deserialize_hand(d: dict) -> GestureResult:
    fingers = tuple(_deserialize_finger(f) for f in d.get("fingers", []))
    if not fingers:
        fingers = tuple(
            FingerState(name=n, flexion=0.0, tip_x=0.0, tip_y=0.0, tip_z=0.0)
            for n in ["thumb", "index", "middle", "ring", "pinky"]
        )
    return GestureResult(
        hand_index=d["hand_index"],
        present=d["present"],
        handedness=d.get("handedness", "Unknown"),
        wrist_x=d.get("wrist_x", 0.0),
        wrist_y=d.get("wrist_y", 0.0),
        pinch=d.get("pinch", 0.0),
        openness=d.get("openness", 0.0),
        fingers=fingers,
        velocity_x=d.get("velocity_x", 0.0),
        velocity_y=d.get("velocity_y", 0.0),
        acceleration_x=d.get("acceleration_x", 0.0),
        acceleration_y=d.get("acceleration_y", 0.0),
        palm_roll=d.get("palm_roll", 0.0),
        palm_pitch=d.get("palm_pitch", 0.0),
        palm_yaw=d.get("palm_yaw", 0.0),
        discrete_gesture=d.get("discrete_gesture", "none"),
    )


def _deserialize_frame(d: dict) -> GestureFrame:
    hands = [_deserialize_hand(h) for h in d.get("hands", [])]
    return GestureFrame(
        frame_id=d["frame_id"],
        captured_at=d["captured_at"],
        processed_at=d["processed_at"],
        hands=hands,
    )


class PlaybackThread(threading.Thread):
    """
    Reads a JSONL recording and publishes frames to gesture_queue
    at the original recorded timing, optionally scaled by a speed multiplier.

    When playback ends, shutdown_event is set so the pipeline stops cleanly.
    """

    def __init__(
        self,
        recording_path: Path,
        gesture_queue: queue.Queue,
        shutdown: threading.Event,
        speed: float = 1.0,
    ) -> None:
        super().__init__(name="PlaybackThread", daemon=True)
        self.recording_path = Path(recording_path)
        self.gesture_queue = gesture_queue
        self.shutdown = shutdown
        self.speed = max(0.01, speed)

    def run(self) -> None:
        if not self.recording_path.exists():
            logger.error("PlaybackThread: file not found: %s", self.recording_path)
            self.shutdown.set()
            return

        frames = self._load()
        if not frames:
            logger.error("PlaybackThread: no frames loaded from %s", self.recording_path)
            self.shutdown.set()
            return

        logger.info(
            "PlaybackThread: replaying %d frames from %s at %.1fx speed",
            len(frames),
            self.recording_path,
            self.speed,
        )

        for i, frame in enumerate(frames):
            if self.shutdown.is_set():
                break

            if i > 0:
                delta = (frame.captured_at - frames[i - 1].captured_at) / self.speed
                sleep_time = max(0.0, delta)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            try:
                self.gesture_queue.put_nowait(frame)
            except queue.Full:
                pass  # Drop frame if dispatcher is busy

        logger.info("PlaybackThread: finished replaying %d frames", len(frames))
        # Give dispatcher a moment to flush remaining frames
        time.sleep(0.5)
        self.shutdown.set()

    def _load(self) -> List[GestureFrame]:
        frames = []
        with open(self.recording_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    frames.append(_deserialize_frame(json.loads(line)))
                except (json.JSONDecodeError, KeyError) as exc:
                    logger.warning("PlaybackThread: skipping malformed line: %s", exc)
        return frames
