"""
Pure gesture calculation functions.

All functions are stateless (no self, no side effects) and operate on
numpy landmark arrays of shape (21, 3) with normalized [0, 1] coordinates.
Pure functions are trivially testable and thread-safe by design.

MediaPipe hand landmark indices:
  0 = Wrist
  1-4 = Thumb (CMC, MCP, IP, Tip)
  5-8 = Index (MCP, PIP, DIP, Tip)
  9-12 = Middle (MCP, PIP, DIP, Tip)
  13-16 = Ring (MCP, PIP, DIP, Tip)
  17-20 = Pinky (MCP, PIP, DIP, Tip)
"""
from __future__ import annotations

import math
from collections import deque
from typing import Dict, Tuple

import numpy as np

from hand_tracking_bridge.gestures.types import FingerState

# ─── Landmark index constants ────────────────────────────────────────────────

WRIST = 0

THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

FINGER_LANDMARKS: Dict[str, Tuple[int, int, int, int]] = {
    "thumb":  (THUMB_CMC,  THUMB_MCP,  THUMB_IP,   THUMB_TIP),
    "index":  (INDEX_MCP,  INDEX_PIP,  INDEX_DIP,  INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    "ring":   (RING_MCP,   RING_PIP,   RING_DIP,   RING_TIP),
    "pinky":  (PINKY_MCP,  PINKY_PIP,  PINKY_DIP,  PINKY_TIP),
}

FINGERTIP_INDICES = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]


# ─── Basic continuous gestures ────────────────────────────────────────────────

def calculate_pinch(
    landmarks: np.ndarray,
    max_distance: float = 0.15,
) -> float:
    """
    Normalized pinch: distance between thumb tip and index tip.
    Returns 1.0 when fully pinched, 0.0 when open.
    Always in [0, 1].
    """
    thumb_tip = landmarks[THUMB_TIP]
    index_tip = landmarks[INDEX_TIP]
    distance = float(np.linalg.norm(thumb_tip - index_tip))
    return float(np.clip(1.0 - distance / max_distance, 0.0, 1.0))


def calculate_openness(
    landmarks: np.ndarray,
    min_distance: float = 0.15,
    max_distance: float = 0.55,
) -> float:
    """
    Average distance of all fingertips from wrist, normalized.
    Returns 1.0 when fully open, 0.0 when closed fist.
    Always in [0, 1].
    """
    wrist = landmarks[WRIST]
    fingertips = landmarks[FINGERTIP_INDICES]
    distances = np.linalg.norm(fingertips - wrist, axis=1)
    avg = float(np.mean(distances))
    return float(np.clip((avg - min_distance) / (max_distance - min_distance), 0.0, 1.0))


# ─── Per-finger flexion ───────────────────────────────────────────────────────

def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """Angle in radians between two vectors. Handles zero-length vectors."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-8 or n2 < 1e-8:
        return 0.0
    cos_angle = np.dot(v1, v2) / (n1 * n2)
    return float(math.acos(float(np.clip(cos_angle, -1.0, 1.0))))


def calculate_finger_flexion(landmarks: np.ndarray, finger_name: str) -> float:
    """
    Flexion at the PIP (middle) joint for a finger.
    Uses dot product of MCP→PIP and PIP→DIP vectors.
    Returns 0.0 = fully extended, 1.0 = fully curled (≥90°).
    Always in [0, 1].
    """
    mcp_idx, pip_idx, dip_idx, _ = FINGER_LANDMARKS[finger_name]
    mcp = landmarks[mcp_idx]
    pip = landmarks[pip_idx]
    dip = landmarks[dip_idx]

    v1 = pip - mcp  # MCP → PIP
    v2 = dip - pip  # PIP → DIP

    angle = _angle_between(v1, v2)
    # 0 rad = straight (flexion=0), π/2 rad = 90° (flexion=1.0)
    return float(np.clip(angle / (math.pi / 2.0), 0.0, 1.0))


def calculate_all_fingers(landmarks: np.ndarray) -> tuple:
    """
    Returns a tuple of FingerState for all 5 fingers.
    Order: thumb, index, middle, ring, pinky.
    """
    results = []
    for i, name in enumerate(["thumb", "index", "middle", "ring", "pinky"]):
        tip_idx = FINGERTIP_INDICES[i]
        tip = landmarks[tip_idx]
        flexion = calculate_finger_flexion(landmarks, name)
        results.append(
            FingerState(
                name=name,
                flexion=flexion,
                tip_x=float(tip[0]),
                tip_y=float(tip[1]),
                tip_z=float(tip[2]),
            )
        )
    return tuple(results)


# ─── Palm orientation ─────────────────────────────────────────────────────────

def calculate_palm_orientation(landmarks: np.ndarray) -> Tuple[float, float, float]:
    """
    Derives palm roll, pitch, yaw from palm plane normal vector.
    Palm normal = cross(wrist→index_mcp, wrist→pinky_mcp)
    Returns (roll, pitch, yaw) in radians.
    """
    wrist = landmarks[WRIST]
    index_mcp = landmarks[INDEX_MCP]
    pinky_mcp = landmarks[PINKY_MCP]

    v_index = index_mcp - wrist
    v_pinky = pinky_mcp - wrist

    normal = np.cross(v_index, v_pinky)
    n = np.linalg.norm(normal)
    if n < 1e-8:
        return 0.0, 0.0, 0.0
    normal = normal / n

    roll = float(math.atan2(float(normal[0]), float(normal[2])))
    pitch = float(math.atan2(float(normal[1]), float(normal[2])))
    yaw = float(math.atan2(float(normal[0]), float(normal[1])))

    return roll, pitch, yaw


# ─── Dynamics (velocity / acceleration) ──────────────────────────────────────

def calculate_velocity(
    current_pos: np.ndarray,
    position_history: deque,
) -> Tuple[float, float]:
    """
    Finite difference velocity from wrist position history.
    history: deque of (timestamp, np.ndarray[x, y]) pairs, oldest first.
    Returns (vx, vy) in normalized units/second. Returns (0, 0) if insufficient history.
    """
    if len(position_history) < 2:
        return 0.0, 0.0

    # Use oldest available point for a wider finite difference window
    t_old, pos_old = position_history[0]
    t_new, pos_new = position_history[-1]
    dt = t_new - t_old
    if dt < 1e-6:
        return 0.0, 0.0

    delta = pos_new - pos_old
    return float(delta[0] / dt), float(delta[1] / dt)


def calculate_acceleration(
    velocity_history: deque,
) -> Tuple[float, float]:
    """
    Finite difference acceleration from velocity history.
    history: deque of (timestamp, (vx, vy)) pairs, oldest first.
    Returns (ax, ay). Returns (0, 0) if insufficient history.
    """
    if len(velocity_history) < 2:
        return 0.0, 0.0

    t_old, (vx_old, vy_old) = velocity_history[0]
    t_new, (vx_new, vy_new) = velocity_history[-1]
    dt = t_new - t_old
    if dt < 1e-6:
        return 0.0, 0.0

    return float((vx_new - vx_old) / dt), float((vy_new - vy_old) / dt)


# ─── Wrist position ───────────────────────────────────────────────────────────

def calculate_wrist_position(landmarks: np.ndarray) -> Tuple[float, float]:
    """
    Returns normalized wrist (x, y) with y flipped (top=1.0, bottom=0.0).
    """
    wrist = landmarks[WRIST]
    x = float(np.clip(wrist[0], 0.0, 1.0))
    y = float(np.clip(1.0 - wrist[1], 0.0, 1.0))  # invert Y
    return x, y
