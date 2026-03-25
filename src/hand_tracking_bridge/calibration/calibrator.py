"""
Per-user calibration system.

AutoCalibrator observes raw gesture values over a warmup window and
derives normalization ranges using the 5th–95th percentile, which is
robust to outliers unlike pure min/max.

Profiles are saved as JSON in calibration_profiles/<name>.json.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CalibrationProfile:
    name: str
    pinch_max: float = 0.15
    openness_min: float = 0.15
    openness_max: float = 0.55
    # Per-finger calibration ranges (name -> (min, max))
    finger_ranges: Dict[str, List[float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationProfile":
        return cls(**data)


class AutoCalibrator:
    """
    Collects gesture statistics and derives calibration ranges.

    Usage:
        cal = AutoCalibrator("alice")
        while not cal.is_calibrated:
            cal.observe(raw_gesture_dict)
        profile = cal.get_profile()
        cal.save()
    """

    def __init__(self, profile_name: str = "default", warmup_frames: int = 90) -> None:
        self.profile_name = profile_name
        self.warmup_frames = warmup_frames

        self._pinch_samples: List[float] = []
        self._openness_samples: List[float] = []
        self._finger_samples: Dict[str, List[float]] = {
            name: [] for name in ["thumb", "index", "middle", "ring", "pinky"]
        }

    def observe(self, pinch: float, openness: float, finger_flexions: Dict[str, float]) -> None:
        """Record one frame of raw gesture values."""
        self._pinch_samples.append(pinch)
        self._openness_samples.append(openness)
        for name, flexion in finger_flexions.items():
            if name in self._finger_samples:
                self._finger_samples[name].append(flexion)

    @property
    def is_calibrated(self) -> bool:
        return len(self._pinch_samples) >= self.warmup_frames

    @property
    def progress(self) -> float:
        """0.0 to 1.0 calibration progress."""
        return min(1.0, len(self._pinch_samples) / self.warmup_frames)

    def get_profile(self) -> CalibrationProfile:
        """
        Derive calibration profile using 5th/95th percentiles.
        More robust than min/max: ignores outlier frames.
        """
        if not self._pinch_samples:
            return CalibrationProfile(name=self.profile_name)

        pinch_p95 = float(np.percentile(self._pinch_samples, 95))
        openness_p5 = float(np.percentile(self._openness_samples, 5))
        openness_p95 = float(np.percentile(self._openness_samples, 95))

        finger_ranges = {}
        for name, samples in self._finger_samples.items():
            if samples:
                finger_ranges[name] = [
                    float(np.percentile(samples, 5)),
                    float(np.percentile(samples, 95)),
                ]

        return CalibrationProfile(
            name=self.profile_name,
            pinch_max=max(0.05, pinch_p95),
            openness_min=max(0.05, openness_p5),
            openness_max=max(0.2, openness_p95),
            finger_ranges=finger_ranges,
        )

    def save(self, profiles_dir: Path = Path("calibration_profiles")) -> Path:
        """Serialize profile to JSON."""
        profiles_dir.mkdir(parents=True, exist_ok=True)
        path = profiles_dir / f"{self.profile_name}.json"
        profile = self.get_profile()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        logger.info("Calibration profile saved to %s", path)
        return path

    def reset(self) -> None:
        """Clear all observations (for live recalibration)."""
        self._pinch_samples.clear()
        self._openness_samples.clear()
        for samples in self._finger_samples.values():
            samples.clear()

    @staticmethod
    def load_profile(
        name: str, profiles_dir: Path = Path("calibration_profiles")
    ) -> CalibrationProfile:
        path = profiles_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Calibration profile not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return CalibrationProfile.from_dict(data)


def run_calibration_wizard(config) -> None:
    """
    Interactive calibration wizard.
    Opens the webcam, collects observations, saves profile.
    """
    import cv2
    import mediapipe as mp
    from hand_tracking_bridge.gestures import calculator as calc

    logger.info("Starting calibration wizard for profile: %s", config.calibration.profile_name)
    print(f"\n=== Calibration Wizard ===")
    print(f"Profile: {config.calibration.profile_name}")
    print(f"Open and close your hand naturally for {config.calibration.warmup_frames} frames.")
    print("Press 'q' to quit early.\n")

    calibrator = AutoCalibrator(
        config.calibration.profile_name,
        config.calibration.warmup_frames,
    )

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(config.capture.camera_index)
    hands_detector = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    while not calibrator.is_calibrated:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_detector.process(rgb)

        if results.multi_hand_landmarks:
            lm_list = results.multi_hand_landmarks[0]
            mp_drawing.draw_landmarks(frame, lm_list, mp_hands.HAND_CONNECTIONS)
            landmarks = np.array(
                [[lm.x, lm.y, lm.z] for lm in lm_list.landmark], dtype=np.float32
            )
            pinch = calc.calculate_pinch(landmarks)
            openness = calc.calculate_openness(landmarks)
            fingers = calc.calculate_all_fingers(landmarks)
            finger_flexions = {f.name: f.flexion for f in fingers}
            calibrator.observe(pinch, openness, finger_flexions)

        progress = calibrator.progress
        bar_width = 300
        filled = int(bar_width * progress)
        cv2.rectangle(frame, (10, frame.shape[0] - 40), (10 + bar_width, frame.shape[0] - 20),
                      (50, 50, 50), -1)
        cv2.rectangle(frame, (10, frame.shape[0] - 40), (10 + filled, frame.shape[0] - 20),
                      (0, 200, 100), -1)
        cv2.putText(frame, f"Calibrating: {int(progress * 100)}%",
                    (10, frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Calibration", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    path = calibrator.save(config.calibration.profiles_dir)
    print(f"\nCalibration complete! Profile saved to {path}")

    cap.release()
    hands_detector.close()
    cv2.destroyAllWindows()
