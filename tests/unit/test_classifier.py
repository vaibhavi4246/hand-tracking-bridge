"""
Unit tests for the discrete gesture classifier.
"""
from __future__ import annotations

import pytest

from hand_tracking_bridge.gestures.classifier import GestureClassifier, _matches_rule
from hand_tracking_bridge.gestures.types import FingerState


def make_fingers(**flexions) -> tuple:
    """
    Create a tuple of FingerState with specified flexions.
    Unspecified fingers default to 0.5 (ambiguous).
    """
    defaults = {"thumb": 0.5, "index": 0.5, "middle": 0.5, "ring": 0.5, "pinky": 0.5}
    defaults.update(flexions)
    return tuple(
        FingerState(name=n, flexion=v, tip_x=0.5, tip_y=0.3, tip_z=0.0)
        for n, v in defaults.items()
    )


def make_fist_fingers() -> tuple:
    return make_fingers(thumb=0.8, index=0.9, middle=0.9, ring=0.9, pinky=0.9)


def make_open_fingers() -> tuple:
    return make_fingers(thumb=0.1, index=0.1, middle=0.1, ring=0.1, pinky=0.1)


def make_peace_fingers() -> tuple:
    return make_fingers(thumb=0.6, index=0.1, middle=0.1, ring=0.9, pinky=0.9)


def make_thumbs_up_fingers() -> tuple:
    return make_fingers(thumb=0.1, index=0.9, middle=0.9, ring=0.9, pinky=0.9)


def make_pointing_fingers() -> tuple:
    return make_fingers(thumb=0.6, index=0.1, middle=0.9, ring=0.9, pinky=0.9)


class TestRuleMatching:
    def test_fist_matches_all_curled(self):
        fingers = make_fist_fingers()
        from hand_tracking_bridge.gestures.classifier import GESTURE_RULES
        assert _matches_rule(fingers, GESTURE_RULES["fist"])

    def test_open_matches_all_extended(self):
        fingers = make_open_fingers()
        from hand_tracking_bridge.gestures.classifier import GESTURE_RULES
        assert _matches_rule(fingers, GESTURE_RULES["open"])

    def test_fist_does_not_match_open(self):
        fingers = make_fist_fingers()
        from hand_tracking_bridge.gestures.classifier import GESTURE_RULES
        assert not _matches_rule(fingers, GESTURE_RULES["open"])


class TestGestureClassifier:
    def _classify_n(self, clf: GestureClassifier, fingers: tuple, n: int) -> str:
        """Submit the same fingers n times and return final label."""
        result = "none"
        for _ in range(n):
            result = clf.classify(fingers)
        return result

    def test_classifies_fist_after_hysteresis(self):
        clf = GestureClassifier(hysteresis_frames=3)
        result = self._classify_n(clf, make_fist_fingers(), 5)
        assert result == "fist"

    def test_classifies_open_hand(self):
        clf = GestureClassifier(hysteresis_frames=3)
        result = self._classify_n(clf, make_open_fingers(), 5)
        assert result == "open"

    def test_classifies_peace(self):
        clf = GestureClassifier(hysteresis_frames=3)
        result = self._classify_n(clf, make_peace_fingers(), 5)
        assert result == "peace"

    def test_classifies_thumbs_up(self):
        clf = GestureClassifier(hysteresis_frames=3)
        result = self._classify_n(clf, make_thumbs_up_fingers(), 5)
        assert result == "thumbs_up"

    def test_classifies_pointing(self):
        clf = GestureClassifier(hysteresis_frames=3)
        result = self._classify_n(clf, make_pointing_fingers(), 5)
        assert result == "pointing"

    def test_hysteresis_prevents_immediate_switch(self):
        """With hysteresis=5, switching gesture takes ≥5 frames to commit."""
        clf = GestureClassifier(hysteresis_frames=5)
        # Warm up with fist
        for _ in range(10):
            clf.classify(make_fist_fingers())
        # Switch to open for only 3 frames — should NOT commit yet
        for _ in range(3):
            label = clf.classify(make_open_fingers())
        assert label == "fist", "Hysteresis should prevent early switch"

    def test_hysteresis_commits_after_enough_frames(self):
        clf = GestureClassifier(hysteresis_frames=5)
        for _ in range(10):
            clf.classify(make_fist_fingers())
        for _ in range(5):
            label = clf.classify(make_open_fingers())
        assert label == "open"

    def test_returns_none_for_ambiguous_pose(self):
        clf = GestureClassifier(hysteresis_frames=1)
        ambiguous = make_fingers(thumb=0.45, index=0.45, middle=0.45, ring=0.45, pinky=0.45)
        result = self._classify_n(clf, ambiguous, 3)
        assert result == "none"

    def test_reset_clears_state(self):
        clf = GestureClassifier(hysteresis_frames=3)
        self._classify_n(clf, make_fist_fingers(), 10)
        clf.reset()
        assert clf._committed_label == "none"
        assert clf._candidate_count == 0
