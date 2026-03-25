"""
Signal smoothing filters for gesture data.

EMAFilter: Classic exponential moving average. Simple, low overhead.
OneEuroFilter: Adaptive cutoff filter (Casiez et al., CHI 2012).
  - Adapts smoothing based on signal velocity: fast gestures get
    less smoothing (responsive), slow movements get more (stable).
  - Eliminates the fixed lag/noise trade-off of EMA.
  Reference: https://cristal.univ-lille.fr/~casiez/1euro/
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Optional


# ─── EMA Filter ──────────────────────────────────────────────────────────────

class EMAFilter:
    """
    Exponential Moving Average filter.
    Maintains independent state per named key, so a single instance
    can smooth multiple signals (e.g. pinch, openness, wrist_x, ...).
    """

    def __init__(self, alpha: float = 0.7) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        self.alpha = alpha
        self._state: Dict[str, float] = {}

    def update(self, key: str, value: float) -> float:
        """Apply EMA and return smoothed value."""
        if key not in self._state:
            self._state[key] = value
            return value
        smoothed = self.alpha * value + (1.0 - self.alpha) * self._state[key]
        self._state[key] = smoothed
        return smoothed

    def reset(self, key: Optional[str] = None) -> None:
        """Reset state for one key, or all keys if key is None."""
        if key is None:
            self._state.clear()
        else:
            self._state.pop(key, None)


# ─── One Euro Filter ─────────────────────────────────────────────────────────

class _LowPassFilter:
    """Internal 1-pole low-pass filter used by OneEuroFilter."""

    def __init__(self) -> None:
        self._initialized = False
        self._value = 0.0

    def filter(self, value: float, alpha: float) -> float:
        if not self._initialized:
            self._value = value
            self._initialized = True
        self._value = alpha * value + (1.0 - alpha) * self._value
        return self._value

    def last_value(self) -> float:
        return self._value

    def reset(self) -> None:
        self._initialized = False
        self._value = 0.0


def _compute_alpha(cutoff: float, rate: float) -> float:
    """Compute EMA alpha from a cutoff frequency and sample rate."""
    tau = 1.0 / (2.0 * math.pi * cutoff)
    te = 1.0 / rate
    return 1.0 / (1.0 + tau / te)


class OneEuroFilter:
    """
    One Euro Filter for low-latency, low-noise signal smoothing.

    Key properties:
    - When the signal is slow (e.g., holding a pose), beta≈0 means heavy
      smoothing via a low min_cutoff frequency.
    - When the signal is fast (e.g., swiping), the cutoff adapts upward
      (beta * |derivative| term) to reduce lag.

    Parameters
    ----------
    min_cutoff : float
        Minimum cutoff frequency in Hz (lower = smoother when still).
        Typical: 0.5–2.0 Hz for hand tracking.
    beta : float
        Speed coefficient. Higher values make the filter more responsive
        to fast movements. Typical: 0.0–1.0.
    d_cutoff : float
        Cutoff frequency for the derivative estimate. Default 1.0 Hz.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.0,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_filter = _LowPassFilter()
        self._dx_filter = _LowPassFilter()
        self._last_time: Optional[float] = None

    def update(self, value: float, timestamp: float) -> float:
        """
        Append a new sample and return the filtered value.

        Parameters
        ----------
        value : float
            Raw sensor value.
        timestamp : float
            Monotonic timestamp in seconds (e.g. time.monotonic()).
        """
        if self._last_time is None:
            self._last_time = timestamp
            self._x_filter.filter(value, 1.0)
            self._dx_filter.filter(0.0, 1.0)
            return value

        dt = timestamp - self._last_time
        if dt <= 0.0:
            # Clock didn't advance — return last filtered value as-is
            return self._x_filter.last_value()
        self._last_time = timestamp

        rate = 1.0 / dt

        # Estimate derivative
        d_alpha = _compute_alpha(self.d_cutoff, rate)
        raw_dx = (value - self._x_filter.last_value()) * rate
        dx = self._dx_filter.filter(raw_dx, d_alpha)

        # Adapt cutoff based on derivative magnitude
        cutoff = self.min_cutoff + self.beta * abs(dx)
        alpha = _compute_alpha(cutoff, rate)

        return self._x_filter.filter(value, alpha)

    def reset(self) -> None:
        self._x_filter.reset()
        self._dx_filter.reset()
        self._last_time = None


class OneEuroFilterBank:
    """
    Manages a bank of named OneEuroFilter instances.
    Mirrors the EMAFilter API for drop-in use in the pipeline.
    """

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._filters: Dict[str, OneEuroFilter] = {}

    def update(self, key: str, value: float, timestamp: float) -> float:
        if key not in self._filters:
            self._filters[key] = OneEuroFilter(
                min_cutoff=self.min_cutoff,
                beta=self.beta,
                d_cutoff=self.d_cutoff,
            )
        return self._filters[key].update(value, timestamp)

    def reset(self, key: Optional[str] = None) -> None:
        if key is None:
            self._filters.clear()
        else:
            if key in self._filters:
                self._filters[key].reset()
