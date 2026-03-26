"""
Real-time theremin-style audio synthesizer sink.

Maps hand gesture data to sound in real-time:
  - wrist_x          → pitch  (pentatonic scale, left=low, right=high)
  - wrist_y          → volume (top=loud, bottom=quiet)
  - openness         → vibrato depth
  - pinch            → octave shift up when > 0.7
  - discrete_gesture → waveform shape:
        open      → sine   (mellow)
        fist      → sawtooth (buzzy/aggressive)
        peace     → square  (retro)
        thumbs_up → triangle (soft synth)
        pointing  → silence (mute)
        none      → sine

Requires: pip install sounddevice
numpy is already a project dependency.
"""
from __future__ import annotations

import logging
import math
import threading
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from hand_tracking_bridge.gestures.types import GestureFrame

from hand_tracking_bridge.sinks.base import OutputSink

logger = logging.getLogger(__name__)

# ─── Pentatonic scale (MIDI semitone offsets from root) ──────────────────────
# Two octaves of A minor pentatonic: A C D E G  (repeats an octave higher)
_PENTATONIC = [0, 3, 5, 7, 10, 12, 15, 17, 19, 22, 24]

# Base note: A3 = 220 Hz
_BASE_FREQ = 220.0

_SAMPLE_RATE = 44100
_CHUNK = 512  # frames per callback

# Gesture → waveform name
_GESTURE_WAVE = {
    "open": "sine",
    "fist": "sawtooth",
    "peace": "square",
    "thumbs_up": "triangle",
    "pointing": "silence",
    "none": "sine",
}


def _midi_to_hz(semitones: float) -> float:
    return _BASE_FREQ * (2.0 ** (semitones / 12.0))


def _pentatonic_freq(x: float, octave_shift: int) -> float:
    """Map x ∈ [0,1] to the nearest pentatonic frequency."""
    idx = round(x * (len(_PENTATONIC) - 1))
    idx = max(0, min(idx, len(_PENTATONIC) - 1))
    semitones = _PENTATONIC[idx] + octave_shift * 12
    return _midi_to_hz(semitones)


def _generate_samples(
    waveform: str,
    phase: float,
    freq: float,
    volume: float,
    vibrato_depth: float,
    n: int,
    sample_rate: int,
) -> tuple[np.ndarray, float]:
    """
    Generate `n` audio samples and return (samples, new_phase).
    Samples are float32 in [-1, 1].
    """
    if waveform == "silence" or volume < 0.001:
        return np.zeros(n, dtype=np.float32), phase

    # Apply vibrato (LFO at 5 Hz modulating pitch ±vibrato_depth semitones)
    t = (phase + np.arange(n)) / sample_rate
    lfo = vibrato_depth * np.sin(2.0 * math.pi * 5.0 * t)
    # Frequency with vibrato (sample-accurate)
    inst_freq = freq * (2.0 ** (lfo / 12.0))
    # Integrate phase
    phases = 2.0 * math.pi * np.cumsum(inst_freq) / sample_rate + (
        2.0 * math.pi * freq * phase / sample_rate
    )

    if waveform == "sine":
        wave = np.sin(phases)
    elif waveform == "sawtooth":
        wave = 2.0 * ((phases / (2.0 * math.pi)) % 1.0) - 1.0
    elif waveform == "square":
        wave = np.sign(np.sin(phases))
    elif waveform == "triangle":
        p = (phases / (2.0 * math.pi)) % 1.0
        wave = 2.0 * np.abs(2.0 * p - 1.0) - 1.0
    else:
        wave = np.sin(phases)

    new_phase = (phase + n) % sample_rate
    return (wave * volume).astype(np.float32), new_phase


class SoundSink(OutputSink):
    """
    Real-time hand-to-sound synthesizer.

    Uses sounddevice's OutputStream with a callback for glitch-free audio.
    Gesture state is updated from the dispatcher thread via atomic float array.
    The audio callback reads that state on every chunk — no locks, no blocking.
    """

    def __init__(self, sample_rate: int = _SAMPLE_RATE, chunk: int = _CHUNK) -> None:
        self._sample_rate = sample_rate
        self._chunk = chunk
        self._stream = None

        # Shared state (written by dispatcher thread, read by audio callback)
        # Layout: [freq, volume, vibrato_depth, waveform_id]
        # waveform_id: 0=sine 1=sawtooth 2=square 3=triangle 4=silence
        self._state = np.array([220.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self._phase: float = 0.0

        self._waveform_names = ["sine", "sawtooth", "square", "triangle", "silence"]

    def open(self) -> None:
        try:
            import sounddevice as sd  # type: ignore[import]
        except ImportError:
            raise ImportError(
                "SoundSink requires 'sounddevice'. Install with: pip install sounddevice"
            )

        self._stream = sd.OutputStream(
            samplerate=self._sample_rate,
            blocksize=self._chunk,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()
        logger.info("SoundSink open — sample_rate=%d chunk=%d", self._sample_rate, self._chunk)

    def send(self, frame: "GestureFrame") -> None:
        """Update synth parameters from the latest gesture frame."""
        # Pick the first present hand (prefer Right hand for melody)
        hand = None
        for h in frame.hands:
            if h.present:
                if h.handedness == "Right":
                    hand = h
                    break
                hand = h  # fallback to Left if no Right found

        if hand is None:
            # Fade to silence
            self._state[1] = 0.0
            return

        # Pitch: wrist_x → pentatonic frequency
        octave_shift = 1 if hand.pinch > 0.7 else 0
        freq = _pentatonic_freq(hand.wrist_x, octave_shift)

        # Volume: wrist_y (top=loud), with smooth ramp via simple filter
        # wrist_y=0 is bottom, 1 is top in our coordinate system
        volume = float(np.clip(hand.wrist_y * 1.2, 0.0, 0.85))

        # Vibrato: openness controls depth (0 = none, 1 = ±1 semitone)
        vibrato = float(np.clip(hand.openness * 1.5, 0.0, 1.5))

        # Waveform
        gesture = hand.discrete_gesture
        wave_name = _GESTURE_WAVE.get(gesture, "sine")
        wave_id = float(self._waveform_names.index(wave_name))

        # Write atomically (numpy element assignment is GIL-protected)
        self._state[0] = freq
        self._state[1] = volume
        self._state[2] = vibrato
        self._state[3] = wave_id

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("SoundSink closed.")

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """Called by sounddevice on the audio thread. Must not block."""
        freq = self._state[0]
        volume = self._state[1]
        vibrato = self._state[2]
        wave_id = int(self._state[3])
        waveform = self._waveform_names[wave_id]

        samples, self._phase = _generate_samples(
            waveform=waveform,
            phase=self._phase,
            freq=freq,
            volume=volume,
            vibrato_depth=vibrato,
            n=frames,
            sample_rate=self._sample_rate,
        )
        outdata[:, 0] = samples
