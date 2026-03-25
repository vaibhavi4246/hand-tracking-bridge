"""
Unit tests for gesture calculator pure functions.

All tests use synthetic landmarks — no MediaPipe, no webcam required.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hand_tracking_bridge.gestures import calculator as calc
from tests.conftest import (
    make_landmarks,
    make_open_hand_landmarks,
    make_pinched_landmarks,
    make_fist_landmarks,
)


class TestPinchCalculation:
    def test_pinch_max_when_tips_coincide(self):
        lm = make_landmarks()
        lm[8] = lm[4].copy()  # index tip = thumb tip
        result = calc.calculate_pinch(lm)
        assert result == pytest.approx(1.0)

    def test_pinch_near_zero_when_far_apart(self, open_hand):
        result = calc.calculate_pinch(open_hand)
        assert result < 0.2

    def test_pinch_high_when_pinched(self, pinched_hand):
        result = calc.calculate_pinch(pinched_hand)
        assert result > 0.8

    def test_pinch_always_in_bounds(self):
        """Property test: for any landmarks, pinch is in [0, 1]."""
        rng = np.random.default_rng(42)
        for _ in range(200):
            lm = rng.random((21, 3)).astype(np.float32)
            result = calc.calculate_pinch(lm)
            assert 0.0 <= result <= 1.0, f"Out of bounds: {result}"

    def test_pinch_respects_max_distance_param(self):
        lm = make_landmarks()
        # Set tips 0.10 apart
        lm[4] = np.array([0.5, 0.5, 0.0], dtype=np.float32)
        lm[8] = np.array([0.5, 0.6, 0.0], dtype=np.float32)
        # With max_distance=0.15, distance=0.10 → pinch = 1 - 0.10/0.15 ≈ 0.333
        result = calc.calculate_pinch(lm, max_distance=0.15)
        assert result == pytest.approx(1.0 - 0.10 / 0.15, abs=0.01)


class TestOpennessCalculation:
    def test_openness_high_for_open_hand(self, open_hand):
        result = calc.calculate_openness(open_hand)
        assert result > 0.4

    def test_openness_always_in_bounds(self):
        rng = np.random.default_rng(99)
        for _ in range(200):
            lm = rng.random((21, 3)).astype(np.float32)
            result = calc.calculate_openness(lm)
            assert 0.0 <= result <= 1.0, f"Out of bounds: {result}"

    def test_openness_low_for_fist(self, fist_hand):
        result = calc.calculate_openness(fist_hand)
        assert result < 0.5


class TestFingerFlexion:
    def test_extended_finger_has_low_flexion(self, open_hand):
        for finger in ["index", "middle", "ring", "pinky"]:
            flexion = calc.calculate_finger_flexion(open_hand, finger)
            assert 0.0 <= flexion <= 1.0, f"{finger} flexion out of bounds: {flexion}"

    def test_flexion_always_in_bounds(self):
        rng = np.random.default_rng(7)
        for _ in range(200):
            lm = rng.random((21, 3)).astype(np.float32)
            for finger in calc.FINGER_LANDMARKS.keys():
                result = calc.calculate_finger_flexion(lm, finger)
                assert 0.0 <= result <= 1.0

    def test_all_fingers_returns_five(self, open_hand):
        fingers = calc.calculate_all_fingers(open_hand)
        assert len(fingers) == 5
        names = [f.name for f in fingers]
        assert names == ["thumb", "index", "middle", "ring", "pinky"]

    def test_straight_finger_has_low_flexion(self):
        """A finger where all joints are collinear should have ~0 flexion."""
        lm = make_landmarks()
        # Make index finger perfectly straight (collinear landmarks)
        lm[5] = np.array([0.5, 0.6, 0.0], dtype=np.float32)  # MCP
        lm[6] = np.array([0.5, 0.5, 0.0], dtype=np.float32)  # PIP
        lm[7] = np.array([0.5, 0.4, 0.0], dtype=np.float32)  # DIP
        lm[8] = np.array([0.5, 0.3, 0.0], dtype=np.float32)  # Tip
        result = calc.calculate_finger_flexion(lm, "index")
        assert result < 0.05, f"Expected near-zero flexion for straight finger, got {result}"

    def test_curled_finger_has_high_flexion(self):
        """A finger where the PIP joint is at 90° should have flexion ~1.0."""
        lm = make_landmarks()
        # Index: MCP at (0.5, 0.5), PIP at (0.5, 0.4), DIP at (0.6, 0.4) — 90° angle
        lm[5] = np.array([0.5, 0.5, 0.0], dtype=np.float32)
        lm[6] = np.array([0.5, 0.4, 0.0], dtype=np.float32)
        lm[7] = np.array([0.6, 0.4, 0.0], dtype=np.float32)
        lm[8] = np.array([0.65, 0.4, 0.0], dtype=np.float32)
        result = calc.calculate_finger_flexion(lm, "index")
        assert result > 0.85, f"Expected high flexion for 90° joint, got {result}"


class TestWristPosition:
    def test_wrist_returns_clamped_values(self):
        lm = make_landmarks(wrist=(0.3, 0.6, 0.0))
        x, y = calc.calculate_wrist_position(lm)
        assert x == pytest.approx(0.3, abs=0.01)
        # Y is inverted: wrist y=0.6 → output y = 1 - 0.6 = 0.4
        assert y == pytest.approx(0.4, abs=0.01)

    def test_wrist_clamps_to_unit_square(self):
        lm = make_landmarks(wrist=(1.5, -0.5, 0.0))
        x, y = calc.calculate_wrist_position(lm)
        assert 0.0 <= x <= 1.0
        assert 0.0 <= y <= 1.0


class TestPalmOrientation:
    def test_returns_three_floats(self, open_hand):
        roll, pitch, yaw = calc.calculate_palm_orientation(open_hand)
        assert isinstance(roll, float)
        assert isinstance(pitch, float)
        assert isinstance(yaw, float)

    def test_handles_degenerate_landmarks(self):
        """Zero-length normal vector should not raise, returns (0, 0, 0)."""
        lm = np.zeros((21, 3), dtype=np.float32)
        result = calc.calculate_palm_orientation(lm)
        assert result == (0.0, 0.0, 0.0)


class TestVelocity:
    def test_zero_velocity_without_history(self):
        from collections import deque
        import numpy as np
        pos = np.array([0.5, 0.5])
        vx, vy = calc.calculate_velocity(pos, deque())
        assert vx == 0.0
        assert vy == 0.0

    def test_velocity_from_history(self):
        from collections import deque
        import numpy as np
        history = deque([
            (0.0, np.array([0.0, 0.0])),
            (1.0, np.array([1.0, 0.5])),
        ])
        current = np.array([1.0, 0.5])
        vx, vy = calc.calculate_velocity(current, history)
        assert vx == pytest.approx(1.0, abs=0.01)
        assert vy == pytest.approx(0.5, abs=0.01)
