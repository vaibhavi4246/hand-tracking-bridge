"""
InferenceThread: MediaPipe hand detection and gesture calculation.

Consumes raw frames from frame_queue, runs MediaPipe, computes all gesture
values, and puts GestureFrame objects on gesture_queue.

Also maintains a viz_queue (maxsize=1) with the annotated frame for the
main-thread visualization renderer.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
import urllib.request
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from hand_tracking_bridge.config import CalibrationConfig, InferenceConfig
from hand_tracking_bridge.gestures import calculator as calc
from hand_tracking_bridge.gestures.classifier import GestureClassifier
from hand_tracking_bridge.gestures.smoother import EMAFilter, OneEuroFilterBank
from hand_tracking_bridge.gestures.types import (
    GestureFrame,
    GestureResult,
    HandData,
    absent_gesture,
)

logger = logging.getLogger(__name__)

_mp_drawing = mp_vision.drawing_utils
_mp_drawing_styles = mp_vision.drawing_styles
_HAND_CONNECTIONS = mp_vision.HandLandmarksConnections.HAND_CONNECTIONS

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
_MODEL_FILENAME = "hand_landmarker.task"

# History depth for velocity/acceleration calculations
_DYNAMICS_HISTORY = 6


def _get_model_path() -> str:
    """Return path to hand_landmarker.task, downloading from Google if absent."""
    local = Path(_MODEL_FILENAME)
    if local.exists():
        return str(local)

    user_dir = Path.home() / ".hand_tracking_bridge"
    user_dir.mkdir(exist_ok=True)
    model_path = user_dir / _MODEL_FILENAME

    if not model_path.exists():
        print(f"[hand-tracker] Downloading hand landmarker model to {model_path} ...")
        logger.info("Downloading hand landmarker model from %s", _MODEL_URL)
        urllib.request.urlretrieve(_MODEL_URL, model_path)
        print("[hand-tracker] Model download complete.")

    return str(model_path)


class _HandState:
    """Per-hand state kept across frames for dynamics and smoothing."""

    def __init__(self, hand_index: int, smoother_type: str, ema_alpha: float,
                 one_euro_min_cutoff: float, one_euro_beta: float) -> None:
        self.hand_index = hand_index
        self.classifier = GestureClassifier(hysteresis_frames=5)
        self.pos_history: deque = deque(maxlen=_DYNAMICS_HISTORY)
        self.vel_history: deque = deque(maxlen=_DYNAMICS_HISTORY)
        self.frame_count = 0

        if smoother_type == "one_euro":
            self.smoother = OneEuroFilterBank(
                min_cutoff=one_euro_min_cutoff, beta=one_euro_beta
            )
        else:
            self.smoother = EMAFilter(alpha=ema_alpha)

    def smooth(self, key: str, value: float, timestamp: float) -> float:
        if isinstance(self.smoother, OneEuroFilterBank):
            return self.smoother.update(key, value, timestamp)
        else:
            return self.smoother.update(key, value)


class InferenceThread(threading.Thread):
    """
    Pulls frames from frame_queue, runs MediaPipe Tasks, emits GestureFrames.
    """

    def __init__(
        self,
        frame_queue: queue.Queue,
        gesture_queue: queue.Queue,
        viz_queue: queue.Queue,
        shutdown: threading.Event,
        config: InferenceConfig,
        calibration_profile=None,
    ) -> None:
        super().__init__(name="InferenceThread", daemon=True)
        self.frame_queue = frame_queue
        self.gesture_queue = gesture_queue
        self.viz_queue = viz_queue
        self.shutdown = shutdown
        self.config = config
        self.calibration_profile = calibration_profile

        self._landmarker = None
        self._hand_states: Dict[int, _HandState] = {}
        self._frame_id = 0

    def run(self) -> None:
        model_path = _get_model_path()
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_hands=self.config.max_num_hands,
            min_hand_detection_confidence=self.config.min_detection_confidence,
            min_hand_presence_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        logger.info("InferenceThread: MediaPipe Tasks initialized")

        while not self.shutdown.is_set():
            try:
                captured_at, frame = self.frame_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            gesture_frame, annotated = self._process(captured_at, frame)

            try:
                self.gesture_queue.put_nowait(gesture_frame)
            except queue.Full:
                pass  # Dispatcher is slow; skip frame

            try:
                self.viz_queue.put_nowait(annotated)
            except queue.Full:
                pass  # Visualization is slow; skip frame

        if self._landmarker:
            self._landmarker.close()
        logger.info("InferenceThread: stopped")

    def _process(self, captured_at: float, frame: np.ndarray) -> Tuple[GestureFrame, np.ndarray]:
        self._frame_id += 1
        annotated = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(captured_at * 1000)

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        processed_at = time.monotonic()

        gesture_results: List[GestureResult] = []

        if result.hand_landmarks:
            for hand_idx, (hand_landmarks, handedness_list) in enumerate(
                zip(result.hand_landmarks, result.handedness)
            ):
                handedness = handedness_list[0].category_name

                # Draw landmarks on annotated frame
                _mp_drawing.draw_landmarks(
                    annotated,
                    hand_landmarks,
                    _HAND_CONNECTIONS,
                    _mp_drawing_styles.get_default_hand_landmarks_style(),
                    _mp_drawing_styles.get_default_hand_connections_style(),
                )

                # Convert to numpy array (21, 3)
                landmarks = np.array(
                    [[lm.x, lm.y, lm.z] for lm in hand_landmarks],
                    dtype=np.float32,
                )

                state = self._get_or_create_state(hand_idx)
                t = processed_at

                # Continuous gestures
                pinch_max = 0.15
                open_min, open_max = 0.15, 0.55
                if self.calibration_profile:
                    pinch_max = self.calibration_profile.pinch_max
                    open_min = self.calibration_profile.openness_min
                    open_max = self.calibration_profile.openness_max

                raw_pinch = calc.calculate_pinch(landmarks, pinch_max)
                raw_open = calc.calculate_openness(landmarks, open_min, open_max)
                wx, wy = calc.calculate_wrist_position(landmarks)

                pinch = state.smooth("pinch", raw_pinch, t)
                openness = state.smooth("openness", raw_open, t)
                wrist_x = state.smooth("wrist_x", wx, t)
                wrist_y = state.smooth("wrist_y", wy, t)

                # Fingers
                fingers = calc.calculate_all_fingers(landmarks)

                # Dynamics
                wrist_pos = np.array([wx, wy])
                state.pos_history.append((t, wrist_pos))
                vx, vy = calc.calculate_velocity(wrist_pos, state.pos_history)
                state.vel_history.append((t, (vx, vy)))
                ax, ay = calc.calculate_acceleration(state.vel_history)

                # Palm orientation
                roll, pitch, yaw = calc.calculate_palm_orientation(landmarks)

                # Discrete gesture
                gesture_label = state.classifier.classify(fingers)

                gesture_results.append(
                    GestureResult(
                        hand_index=hand_idx,
                        present=True,
                        handedness=handedness,
                        wrist_x=wrist_x,
                        wrist_y=wrist_y,
                        pinch=pinch,
                        openness=openness,
                        fingers=fingers,
                        velocity_x=vx,
                        velocity_y=vy,
                        acceleration_x=ax,
                        acceleration_y=ay,
                        palm_roll=roll,
                        palm_pitch=pitch,
                        palm_yaw=yaw,
                        discrete_gesture=gesture_label,
                    )
                )

        # Pad absent hands to always have entries for both hand slots
        present_indices = {r.hand_index for r in gesture_results}
        for i in range(self.config.max_num_hands):
            if i not in present_indices:
                gesture_results.insert(i, absent_gesture(i))

        # Overlay debug text
        self._draw_overlay(annotated, gesture_results, processed_at)

        return (
            GestureFrame(
                frame_id=self._frame_id,
                captured_at=captured_at,
                processed_at=processed_at,
                hands=gesture_results,
            ),
            annotated,
        )

    def _get_or_create_state(self, hand_idx: int) -> _HandState:
        if hand_idx not in self._hand_states:
            self._hand_states[hand_idx] = _HandState(
                hand_idx,
                smoother_type=self.config.smoother,
                ema_alpha=self.config.ema_alpha,
                one_euro_min_cutoff=self.config.one_euro_min_cutoff,
                one_euro_beta=self.config.one_euro_beta,
            )
        return self._hand_states[hand_idx]

    def _draw_overlay(
        self,
        frame: np.ndarray,
        hands: List[GestureResult],
        processed_at: float,
    ) -> None:
        y = 30
        for hand in hands:
            if not hand.present:
                continue
            lines = [
                f"Hand {hand.hand_index} ({hand.handedness})",
                f"  pinch={hand.pinch:.2f}  open={hand.openness:.2f}",
                f"  wrist=({hand.wrist_x:.2f}, {hand.wrist_y:.2f})",
                f"  gesture={hand.discrete_gesture}",
                f"  fingers: " + " ".join(f"{f.name[0]}={f.flexion:.1f}" for f in hand.fingers),
            ]
            for line in lines:
                cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (0, 255, 0), 1, cv2.LINE_AA)
                y += 22
            y += 10
