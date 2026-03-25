"""
Immutable data types for gesture pipeline.
Frozen dataclasses are safe to pass across thread boundaries without locks.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class FingerState:
    """Computed state for a single finger."""

    name: str  # "thumb", "index", "middle", "ring", "pinky"
    flexion: float  # 0.0 = fully extended, 1.0 = fully curled
    tip_x: float  # normalized [0, 1]
    tip_y: float  # normalized [0, 1]
    tip_z: float  # depth (relative)


@dataclass(frozen=True)
class HandData:
    """Raw per-frame data from MediaPipe for one hand."""

    hand_index: int  # 0 or 1
    handedness: str  # "Left" or "Right"
    landmarks: np.ndarray  # shape (21, 3), dtype float32 — normalized [0,1]
    captured_at: float  # time.monotonic() at frame capture

    def __hash__(self) -> int:
        return hash((self.hand_index, self.handedness, self.captured_at))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandData):
            return NotImplemented
        return (
            self.hand_index == other.hand_index
            and self.handedness == other.handedness
            and self.captured_at == other.captured_at
        )


@dataclass(frozen=True)
class GestureResult:
    """Fully computed gesture data for one hand in one frame."""

    hand_index: int
    present: bool
    handedness: str  # "Left" or "Right"

    # Continuous gestures
    wrist_x: float  # [0, 1], left=0, right=1
    wrist_y: float  # [0, 1], bottom=0, top=1
    pinch: float  # [0, 1], 1=fully pinched
    openness: float  # [0, 1], 1=fully open

    # Per-finger states (thumb=0 ... pinky=4)
    fingers: tuple  # tuple[FingerState, ...]

    # Dynamics
    velocity_x: float  # wrist pixels/second (normalized)
    velocity_y: float
    acceleration_x: float
    acceleration_y: float

    # Palm orientation (radians)
    palm_roll: float
    palm_pitch: float
    palm_yaw: float

    # Discrete gesture classification
    discrete_gesture: str  # "fist" | "open" | "peace" | "thumbs_up" | "pointing" | "none"

    def to_dict(self) -> dict:
        return {
            "hand_index": self.hand_index,
            "present": self.present,
            "handedness": self.handedness,
            "wrist_x": self.wrist_x,
            "wrist_y": self.wrist_y,
            "pinch": self.pinch,
            "openness": self.openness,
            "fingers": [
                {
                    "name": f.name,
                    "flexion": f.flexion,
                    "tip_x": f.tip_x,
                    "tip_y": f.tip_y,
                }
                for f in self.fingers
            ],
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "acceleration_x": self.acceleration_x,
            "acceleration_y": self.acceleration_y,
            "palm_roll": self.palm_roll,
            "palm_pitch": self.palm_pitch,
            "palm_yaw": self.palm_yaw,
            "discrete_gesture": self.discrete_gesture,
        }


# Sentinel: empty gesture result when no hand is detected
def absent_gesture(hand_index: int) -> GestureResult:
    empty_finger = FingerState(name="", flexion=0.0, tip_x=0.0, tip_y=0.0, tip_z=0.0)
    return GestureResult(
        hand_index=hand_index,
        present=False,
        handedness="Unknown",
        wrist_x=0.0,
        wrist_y=0.0,
        pinch=0.0,
        openness=0.0,
        fingers=(empty_finger,) * 5,
        velocity_x=0.0,
        velocity_y=0.0,
        acceleration_x=0.0,
        acceleration_y=0.0,
        palm_roll=0.0,
        palm_pitch=0.0,
        palm_yaw=0.0,
        discrete_gesture="none",
    )


@dataclass
class GestureFrame:
    """Complete gesture data for one video frame across all detected hands."""

    frame_id: int
    captured_at: float  # time.monotonic() at camera capture
    processed_at: float  # time.monotonic() after MediaPipe inference
    hands: list  # list[GestureResult]

    @property
    def latency_ms(self) -> float:
        return (self.processed_at - self.captured_at) * 1000.0

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "captured_at": self.captured_at,
            "processed_at": self.processed_at,
            "latency_ms": self.latency_ms,
            "hands": [h.to_dict() for h in self.hands],
        }
