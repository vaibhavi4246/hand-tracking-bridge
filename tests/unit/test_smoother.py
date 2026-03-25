"""
Unit tests for EMAFilter and OneEuroFilter.
"""
from __future__ import annotations

import math
import time

import pytest

from hand_tracking_bridge.gestures.smoother import (
    EMAFilter,
    OneEuroFilter,
    OneEuroFilterBank,
)


class TestEMAFilter:
    def test_first_update_returns_raw_value(self):
        f = EMAFilter(alpha=0.7)
        result = f.update("x", 0.8)
        assert result == pytest.approx(0.8)

    def test_smooths_toward_target(self):
        f = EMAFilter(alpha=0.7)
        f.update("x", 0.0)
        # Feed 1.0 repeatedly — should converge toward 1.0
        for _ in range(30):
            result = f.update("x", 1.0)
        assert result > 0.99

    def test_multiple_keys_are_independent(self):
        f = EMAFilter(alpha=0.7)
        f.update("a", 1.0)
        f.update("b", 0.0)
        assert f._state["a"] == pytest.approx(1.0)
        assert f._state["b"] == pytest.approx(0.0)

    def test_reset_single_key(self):
        f = EMAFilter(alpha=0.7)
        f.update("x", 0.5)
        f.update("y", 0.9)
        f.reset("x")
        assert "x" not in f._state
        assert "y" in f._state

    def test_reset_all_keys(self):
        f = EMAFilter(alpha=0.7)
        f.update("x", 0.5)
        f.update("y", 0.9)
        f.reset()
        assert f._state == {}

    def test_invalid_alpha_raises(self):
        with pytest.raises(ValueError):
            EMAFilter(alpha=0.0)
        with pytest.raises(ValueError):
            EMAFilter(alpha=1.1)

    def test_output_bounded_for_bounded_inputs(self):
        """EMA output should stay within [0, 1] if inputs are always in [0, 1]."""
        f = EMAFilter(alpha=0.7)
        import random
        rng = random.Random(42)
        result = 0.5
        for _ in range(1000):
            val = rng.random()
            result = f.update("x", val)
            assert 0.0 <= result <= 1.0


class TestOneEuroFilter:
    def test_first_update_returns_raw_value(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
        result = f.update(0.5, timestamp=0.0)
        assert result == pytest.approx(0.5)

    def test_convergence_to_constant_signal(self):
        f = OneEuroFilter(min_cutoff=2.0, beta=0.0)
        t = 0.0
        result = 0.0
        for i in range(100):
            t += 1.0 / 30.0
            result = f.update(1.0, timestamp=t)
        assert result > 0.99, f"Expected convergence to 1.0, got {result}"

    def test_faster_signal_gets_less_smoothing(self):
        """
        With beta > 0, a fast-changing signal should track better than a slow
        signal. We test this by measuring final error on a step input.
        """
        # Low beta (high smoothing lag on fast signal)
        f_slow = OneEuroFilter(min_cutoff=1.0, beta=0.0)
        # High beta (less smoothing on fast signal)
        f_fast = OneEuroFilter(min_cutoff=1.0, beta=2.0)

        t = 0.0
        for i in range(50):
            t += 1.0 / 30.0
            target = 1.0 if i > 5 else 0.0
            f_slow.update(target, t)
            f_fast.update(target, t)

        # After step at frame 5, fast beta should track closer to 1.0
        t += 1.0 / 30.0
        slow_val = f_slow.update(1.0, t)
        fast_val = f_fast.update(1.0, t)
        assert fast_val >= slow_val, "High beta should track step input faster"

    def test_same_timestamp_returns_last_filtered(self):
        f = OneEuroFilter()
        f.update(0.5, 1.0)
        result = f.update(0.8, 1.0)  # Same timestamp — no update
        assert result == pytest.approx(0.5, abs=0.01)

    def test_reset_clears_state(self):
        f = OneEuroFilter()
        f.update(0.5, 0.0)
        f.update(0.8, 0.033)
        f.reset()
        assert f._last_time is None

    def test_output_near_input_for_stationary_signal(self):
        """Stationary signal: filter should not add constant offset."""
        f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
        t = 0.0
        for _ in range(60):
            t += 1.0 / 30.0
            result = f.update(0.5, t)
        assert result == pytest.approx(0.5, abs=0.01)


class TestOneEuroFilterBank:
    def test_independent_keys(self):
        bank = OneEuroFilterBank(min_cutoff=1.0, beta=0.0)
        t = 0.0
        for _ in range(50):
            t += 1.0 / 30.0
            bank.update("a", 1.0, t)
            bank.update("b", 0.0, t)
        assert bank.update("a", 1.0, t + 0.033) > 0.99
        assert bank.update("b", 0.0, t + 0.033) < 0.01

    def test_reset_single_key(self):
        bank = OneEuroFilterBank()
        bank.update("x", 0.5, 0.0)
        bank.reset("x")
        assert "x" not in bank._filters

    def test_reset_all(self):
        bank = OneEuroFilterBank()
        bank.update("x", 0.5, 0.0)
        bank.update("y", 0.9, 0.0)
        bank.reset()
        assert bank._filters == {}
