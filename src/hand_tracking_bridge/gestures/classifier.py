"""
Rule-based discrete gesture classifier with temporal hysteresis.

Each gesture is defined as a dict of finger_name -> (min_flexion, max_flexion).
The classifier requires N consecutive frames in agreement before committing
to a new label, preventing flickering on borderline poses.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Optional, Tuple

from hand_tracking_bridge.gestures.types import FingerState

# ─── Gesture rule table ───────────────────────────────────────────────────────
# Each entry: finger_name -> (min_flexion, max_flexion)
# Fingers not listed are unconstrained ("don't care").

GestureRules = Dict[str, Tuple[float, float]]

GESTURE_RULES: Dict[str, GestureRules] = {
    "fist": {
        "thumb":  (0.45, 1.0),
        "index":  (0.55, 1.0),
        "middle": (0.55, 1.0),
        "ring":   (0.55, 1.0),
        "pinky":  (0.55, 1.0),
    },
    "open": {
        "thumb":  (0.0, 0.45),
        "index":  (0.0, 0.35),
        "middle": (0.0, 0.35),
        "ring":   (0.0, 0.35),
        "pinky":  (0.0, 0.35),
    },
    "peace": {
        "index":  (0.0, 0.35),
        "middle": (0.0, 0.35),
        "ring":   (0.55, 1.0),
        "pinky":  (0.55, 1.0),
    },
    "thumbs_up": {
        "thumb":  (0.0, 0.35),
        "index":  (0.55, 1.0),
        "middle": (0.55, 1.0),
        "ring":   (0.55, 1.0),
        "pinky":  (0.55, 1.0),
    },
    "pointing": {
        "index":  (0.0, 0.35),
        "middle": (0.55, 1.0),
        "ring":   (0.55, 1.0),
        "pinky":  (0.55, 1.0),
    },
}

GESTURE_PRIORITY = ["fist", "open", "thumbs_up", "peace", "pointing"]


def _matches_rule(
    fingers: tuple,  # tuple[FingerState, ...]
    rules: GestureRules,
) -> bool:
    """Check if all constrained fingers are within their allowed flexion range."""
    finger_map = {f.name: f.flexion for f in fingers}
    for finger_name, (min_flex, max_flex) in rules.items():
        flexion = finger_map.get(finger_name)
        if flexion is None:
            return False
        if not (min_flex <= flexion <= max_flex):
            return False
    return True


class GestureClassifier:
    """
    Classifies a tuple of FingerState objects into a discrete gesture label.

    Temporal hysteresis prevents rapid flickering between gesture labels:
    a new label is only committed after `hysteresis_frames` consecutive
    frames agree on the same classification.
    """

    def __init__(self, hysteresis_frames: int = 5) -> None:
        self.hysteresis_frames = hysteresis_frames
        self._candidate_label: str = "none"
        self._candidate_count: int = 0
        self._committed_label: str = "none"

    def classify(self, fingers: tuple) -> str:
        """
        Return the current committed gesture label.
        Updates internal hysteresis state.
        """
        raw_label = self._raw_classify(fingers)

        if raw_label == self._candidate_label:
            self._candidate_count += 1
        else:
            self._candidate_label = raw_label
            self._candidate_count = 1

        if self._candidate_count >= self.hysteresis_frames:
            self._committed_label = self._candidate_label

        return self._committed_label

    def _raw_classify(self, fingers: tuple) -> str:
        """Single-frame classification without hysteresis."""
        for gesture_name in GESTURE_PRIORITY:
            rules = GESTURE_RULES[gesture_name]
            if _matches_rule(fingers, rules):
                return gesture_name
        return "none"

    def reset(self) -> None:
        self._candidate_label = "none"
        self._candidate_count = 0
        self._committed_label = "none"
