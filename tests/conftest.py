"""
Shared test fixtures for the hand tracking bridge test suite.

Provides factory functions and pytest fixtures for creating synthetic
21-landmark numpy arrays representing various hand poses.

MediaPipe landmark indices:
  0=Wrist, 1-4=Thumb, 5-8=Index, 9-12=Middle, 13-16=Ring, 17-20=Pinky
  Each landmark: (x, y, z) normalized to [0, 1]
"""
from __future__ import annotations

import time
from typing import Any, Dict

import numpy as np
import pytest

from hand_tracking_bridge.gestures.types import FingerState, GestureFrame, GestureResult


# ─── Landmark factory ─────────────────────────────────────────────────────────

def make_landmarks(
    wrist: tuple = (0.5, 0.7, 0.0),
    **overrides: tuple,
) -> np.ndarray:
    """
    Create a synthetic 21-landmark array with anatomically plausible defaults.

    Parameters
    ----------
    wrist : (x, y, z)
        Wrist position.
    **overrides : int -> (x, y, z)
        Landmark index overrides. Keys are landmark indices as strings, e.g. '4' for thumb tip.

    Returns
    -------
    np.ndarray of shape (21, 3), dtype float32
    """
    lm = np.zeros((21, 3), dtype=np.float32)

    # Wrist
    lm[0] = wrist

    # Thumb landmarks (slightly extended by default)
    lm[1] = (0.4, 0.65, 0.0)   # CMC
    lm[2] = (0.35, 0.60, 0.0)  # MCP
    lm[3] = (0.30, 0.55, 0.0)  # IP
    lm[4] = (0.28, 0.50, 0.0)  # Tip

    # Index finger (extended)
    lm[5] = (0.45, 0.60, 0.0)  # MCP
    lm[6] = (0.44, 0.48, 0.0)  # PIP
    lm[7] = (0.44, 0.38, 0.0)  # DIP
    lm[8] = (0.44, 0.28, 0.0)  # Tip

    # Middle finger (extended)
    lm[9]  = (0.50, 0.58, 0.0)  # MCP
    lm[10] = (0.50, 0.45, 0.0)  # PIP
    lm[11] = (0.50, 0.35, 0.0)  # DIP
    lm[12] = (0.50, 0.24, 0.0)  # Tip

    # Ring finger (extended)
    lm[13] = (0.55, 0.60, 0.0)  # MCP
    lm[14] = (0.56, 0.48, 0.0)  # PIP
    lm[15] = (0.56, 0.38, 0.0)  # DIP
    lm[16] = (0.56, 0.28, 0.0)  # Tip

    # Pinky (extended)
    lm[17] = (0.60, 0.63, 0.0)  # MCP
    lm[18] = (0.62, 0.53, 0.0)  # PIP
    lm[19] = (0.62, 0.45, 0.0)  # DIP
    lm[20] = (0.62, 0.37, 0.0)  # Tip

    for idx_str, val in overrides.items():
        lm[int(idx_str)] = val

    return lm


def make_fist_landmarks() -> np.ndarray:
    """All fingers curled toward wrist."""
    lm = make_landmarks()
    wrist = lm[0]
    # Move all finger landmarks near wrist to simulate curl
    for group_start in [1, 5, 9, 13, 17]:
        for offset in range(4):
            # Gradually bring each landmark closer to wrist
            factor = (offset + 1) / 4.0
            tip = lm[group_start]
            lm[group_start + offset] = wrist + (tip - wrist) * (1 - factor * 0.85)
    return lm


def make_open_hand_landmarks() -> np.ndarray:
    """All fingers extended, fingertips far from wrist."""
    return make_landmarks()  # default pose is open hand


def make_pinched_landmarks() -> np.ndarray:
    """Thumb tip and index tip very close together."""
    lm = make_landmarks()
    # Move index tip (8) to coincide with thumb tip (4)
    lm[8] = lm[4].copy()
    return lm


def make_peace_landmarks() -> np.ndarray:
    """Index and middle extended, ring and pinky curled."""
    lm = make_landmarks()
    # Curl ring and pinky
    wrist = lm[0]
    for group_start in [13, 17]:  # ring, pinky
        for offset in range(4):
            factor = (offset + 1) / 4.0
            tip = lm[group_start]
            lm[group_start + offset] = wrist + (tip - wrist) * (1 - factor * 0.85)
    return lm


# ─── Gesture result factory ────────────────────────────────────────────────────

def make_finger_state(name: str, flexion: float = 0.0) -> FingerState:
    return FingerState(name=name, flexion=flexion, tip_x=0.5, tip_y=0.3, tip_z=0.0)


def make_gesture_result(hand_index: int = 0, **kwargs: Any) -> GestureResult:
    defaults = dict(
        present=True,
        handedness="Right",
        wrist_x=0.5,
        wrist_y=0.5,
        pinch=0.0,
        openness=0.8,
        fingers=tuple(make_finger_state(n) for n in ["thumb", "index", "middle", "ring", "pinky"]),
        velocity_x=0.0,
        velocity_y=0.0,
        acceleration_x=0.0,
        acceleration_y=0.0,
        palm_roll=0.0,
        palm_pitch=0.0,
        palm_yaw=0.0,
        discrete_gesture="open",
    )
    defaults.update(kwargs)
    return GestureResult(hand_index=hand_index, **defaults)


def make_gesture_frame(frame_id: int = 1) -> GestureFrame:
    t = time.monotonic()
    return GestureFrame(
        frame_id=frame_id,
        captured_at=t,
        processed_at=t + 0.015,
        hands=[make_gesture_result(0), make_gesture_result(1, present=False)],
    )


# ─── Pytest fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def open_hand():
    return make_open_hand_landmarks()


@pytest.fixture
def fist_hand():
    return make_fist_landmarks()


@pytest.fixture
def pinched_hand():
    return make_pinched_landmarks()


@pytest.fixture
def peace_hand():
    return make_peace_landmarks()


@pytest.fixture
def gesture_frame():
    return make_gesture_frame()
