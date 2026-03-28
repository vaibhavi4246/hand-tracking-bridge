# Hand Tracking Bridge

A real-time hand gesture pipeline that bridges MediaPipe hand tracking with TouchDesigner, web browsers, and any OSC-compatible software.


---

## Features

| Category | Capability |
|----------|-----------|
| **Detection** | Up to 2 hands @ 30 FPS via MediaPipe Tasks API |
| **Gestures** | Pinch, openness, per-finger flexion (0–1), palm orientation (roll/pitch/yaw), wrist velocity & acceleration |
| **Classification** | Discrete gestures: `fist`, `open`, `peace`, `thumbs_up`, `pointing` with temporal hysteresis |
| **Smoothing** | One Euro Filter (adaptive, low-latency) + EMA |
| **Output** | OSC (TouchDesigner), WebSocket (browser), JSONL recording |
| **Dashboard** | Live metrics UI at `localhost:8000` — skeleton canvas, gesture bars, FPS/latency, **built-in theremin synth** |
| **Infinite Void** | 3D hand-controlled interactive scene at `localhost:8000/void` — grab, throw, spawn objects + sound synthesis |
| **Calibration** | Per-user profiles with auto-calibration (5th/95th percentile) |
| **Playback** | Replay recordings without webcam — great for TD patch development |
| **Tests** | pytest unit + integration tests, GitHub Actions CI on Python 3.10–3.12 |

---

## Installation

Requires **Python 3.10+** (including 3.13) and a webcam.

```bash
# Clone the repo
git clone https://github.com/vaibhavi4246/hand-tracking-bridge
cd hand-tracking-bridge

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install (core only)
pip install -e .

# Install with dashboard + WebSocket support
pip install -e ".[dashboard,websocket]"

# Install with dashboard + sound synth (server-side)
pip install -e ".[dashboard,sound]"

# Install everything
pip install -e ".[all]"

# Install with dev tools (tests, linting)
pip install -e ".[dev]"
```

> **First run:** the MediaPipe hand landmarker model (~8 MB) is automatically downloaded to `~/.hand_tracking_bridge/hand_landmarker.task` on first launch.

---

## Quick Start

```bash
# Basic — OSC to TouchDesigner on port 7000
hand-tracker

# With live web dashboard + Infinite Void at http://localhost:8000
hand-tracker --dashboard

# Dashboard + theremin synth (server-side audio output)
hand-tracker --dashboard --sound

# Disable the OpenCV preview window (useful on headless setups)
hand-tracker --dashboard --no-window

# Custom OSC target
hand-tracker --osc-host 192.168.1.50 --osc-port 9000

# Calibrate for your hand, then use the profile
hand-tracker --calibrate --profile alice
hand-tracker --profile alice

# Record a session, replay later
hand-tracker --record recordings/session.jsonl
hand-tracker --playback recordings/session.jsonl --speed 0.5

# All options
hand-tracker --help
```

---

## Dashboard — Sound Synth

Open **http://localhost:8000** while `hand-tracker --dashboard` is running, then click **♪ SOUND OFF** in the header to enable the browser-side theremin synthesizer (no extra install needed — runs entirely via Web Audio API).

| Hand input | Effect |
|---|---|
| `wrist_x` left ↔ right | Pitch — pentatonic scale A3–A5, quantized to no wrong notes |
| `wrist_y` bottom ↔ top | Volume |
| `openness` | Vibrato depth (LFO at 5 Hz) |
| `pinch > 0.7` | Octave shift up |
| `open` hand 🖐 | Sine wave (mellow) |
| `fist` ✊ | Sawtooth (buzzy) |
| `peace` ✌️ | Square wave (retro) |
| `thumbs_up` 👍 | Triangle wave (soft) |
| `pointing` ☝️ | Mute |

A live **oscilloscope** in the Sound Synth card shows the waveform in real time. All parameter changes ramp smoothly (50 ms) to prevent audio clicks.

For server-side audio output (plays through the machine running `hand-tracker`), add the `--sound` flag and install `sounddevice`:

```bash
pip install sounddevice
hand-tracker --dashboard --sound
```

---

## Particle Void — 3D Hand-Controlled Orb

Open **http://localhost:8000/void** while `hand-tracker --dashboard` is running.

A 5 500-particle orb floats in infinite space. Use your hands to sculpt, spin, zoom, and explode it.

### Opening the Particle Void

```
http://localhost:8000/void
```

No extra flags needed — the `/void` page shares the same server as the dashboard.

### Hand Controls

| Gesture / Action | Effect |
|-----------------|--------|
| **Swipe hand left/right** | Spins the orb — velocity impulse, orb coasts with physics friction |
| **Swipe hand up/down** | Tilts the orb vertically |
| **Hold open palm** 🖐 | Continuously **repels** particles near your cursor (gravity well) |
| **Hold closed fist** ✊ | Continuously **attracts** particles toward your cursor |
| **Open palm → transition** | One-shot **explosion** burst (particles fly outward) |
| **Fist → transition** | One-shot **implosion** burst (particles collapse inward) |
| **Pinch** (thumb + index) | Compresses all particles toward the center |
| **Move hand fast** | Particles in your path get pushed (velocity wake effect) |
| **Spread both hands apart** | Zooms the orb out — particles expand |
| **Bring both hands together** | Zooms the orb in — particles compress |

### How Movement Works

- **Swipe-based rotation**: hand velocity (not position) drives the orb's spin as an impulse. Swipe left → orb spins left and coasts to rest via physics friction (`×0.96` per frame). No hands → settles to a slow idle spin.
- **Gravity well**: each hand cursor creates a spatial influence zone (~2 world-unit radius). Holding an open palm repels particles within range; holding a fist attracts them. Other gestures use openness to decide (open > 0.65 = repel, else attract). Coordinates are computed in the orb's local space, so the effect tracks correctly even after the orb has rotated.
- **Two-hand zoom**: the distance between your two wrists is compared to where they were when the second hand entered frame. Spread = scale up, close = scale down. Rotation impulses are disabled during zoom so the two modes don't fight.
- **Pinch compression**: holding a pinch above 12% continuously draws particles inward; releasing lets spring physics restore them.
- **Gesture bursts**: transitioning to `open` or `fist` fires a one-shot radial force that decays over ~55 frames. The orb light color shifts (red during fist, white during pinch, blue default) and pulses brighter during bursts.
- **Velocity wake**: moving your hand quickly pushes nearby particles in the direction of motion, leaving a visible trail through the orb.

---

## OSC Address Reference

All messages sent as `OscBundle` for atomic delivery. Addresses per hand:

| Address | Type | Range | Description |
|---------|------|-------|-------------|
| `/hand/{i}/present` | int | 0 or 1 | Hand detected |
| `/hand/{i}/wrist/x` | float | 0–1 | Wrist X (left=0, right=1) |
| `/hand/{i}/wrist/y` | float | 0–1 | Wrist Y (bottom=0, top=1) |
| `/hand/{i}/pinch` | float | 0–1 | Thumb–index distance (1=pinched) |
| `/hand/{i}/openness` | float | 0–1 | Average fingertip spread |
| `/hand/{i}/gesture` | string | — | `fist` / `open` / `peace` / `thumbs_up` / `pointing` / `none` |
| `/hand/{i}/palm/roll` | float | radians | Palm roll |
| `/hand/{i}/palm/pitch` | float | radians | Palm pitch |
| `/hand/{i}/palm/yaw` | float | radians | Palm yaw |
| `/hand/{i}/velocity/x` | float | — | Wrist horizontal velocity |
| `/hand/{i}/velocity/y` | float | — | Wrist vertical velocity |
| `/hand/{i}/finger/thumb` | float | 0–1 | Thumb flexion |
| `/hand/{i}/finger/index` | float | 0–1 | Index flexion |
| `/hand/{i}/finger/middle` | float | 0–1 | Middle flexion |
| `/hand/{i}/finger/ring` | float | 0–1 | Ring flexion |
| `/hand/{i}/finger/pinky` | float | 0–1 | Pinky flexion |

---

## TouchDesigner Setup

1. Add an **OSC In CHOP** → set Port to `7000`
2. Use a **Select CHOP** to pick specific channels (e.g. `hand_0_pinch`)
3. Use a **Math CHOP** to remap 0–1 to your target range

See [TOUCHDESIGNER_EXAMPLES.md](TOUCHDESIGNER_EXAMPLES.md) for 8 complete example patches.

---

## Architecture

```
Webcam
  │
  ▼ (bounded queue, maxsize=2 — drops stale frames)
CaptureThread
  │
  ▼ (frame_queue)
InferenceThread  ←── MediaPipe Tasks API + GestureCalculator + OneEuroFilter + GestureClassifier
  │
  ▼ (gesture_queue)
DispatcherThread ──► OSCSink        → TouchDesigner (UDP:7000)
                ──► WebSocketSink   → External WS clients (WS:8765)
                ──► FileSink        → JSONL recording
                ──► DashboardSink   → FastAPI /ws → browser dashboard + Infinite Void
                ──► SoundSink       → sounddevice theremin synth (server-side, opt-in)

Main thread: OpenCV visualization window
FastAPI thread: http://localhost:8000  (dashboard + /void)
```

Key design decisions:

- **Bounded queues + frame-drop policy** — system always operates on the most recent frame; slow inference never builds latency backlog
- **Frozen dataclasses (`GestureFrame`)** — immutable across thread boundaries, no locks needed
- **Pure functions in `calculator.py`** — no state, fully testable without mocking
- **`OutputSink` ABC** — adding MIDI/DMX/dashboard output requires zero pipeline changes (Open/Closed Principle)
- **One Euro Filter** over EMA — adapts smoothing cutoff to signal velocity (Casiez et al., CHI 2012)
- **MediaPipe Tasks API** — compatible with Python 3.13 and mediapipe 0.10+

---

## Gesture Calculations

### Finger Flexion
PIP joint angle via dot product of bone vectors:
```
v1 = MCP → PIP
v2 = PIP → DIP
flexion = arccos(dot(v1, v2) / (|v1| * |v2|)) / (π/2)   ∈ [0, 1]
```

### Palm Orientation
Palm plane normal from cross product:
```
normal = cross(wrist→index_mcp, wrist→pinky_mcp)
roll  = atan2(normal.x, normal.z)
pitch = atan2(normal.y, normal.z)
yaw   = atan2(normal.x, normal.y)
```

### Smoothing — One Euro Filter
Adapts the cutoff frequency based on signal derivative:
```
cutoff = min_cutoff + beta * |dx/dt|
```
Fast gestures → higher cutoff → less lag. Stationary pose → lower cutoff → less noise.

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=hand_tracking_bridge
```

Tests cover:
- All gesture calculation functions (pure unit tests, no hardware needed)
- EMA and One Euro Filter convergence and edge cases
- Gesture classifier hysteresis timing
- OSCSink integration (real UDP socket on ephemeral port)

---

## Project Structure

```
hand-tracking-bridge/
├── pyproject.toml                   # Package config, CLI entry point
├── src/hand_tracking_bridge/
│   ├── cli.py                       # hand-tracker entry point
│   ├── config.py                    # Pydantic AppConfig
│   ├── pipeline/                    # Threaded capture / inference / dispatch
│   ├── gestures/                    # types, calculator, smoother, classifier
│   ├── sinks/                       # OSCSink, WebSocketSink, FileSink, DashboardSink, SoundSink
│   ├── calibration/                 # AutoCalibrator + profiles
│   ├── dashboard/
│   │   ├── server.py                # FastAPI server (/, /void, /ws, /health)
│   │   └── static/
│   │       ├── index.html           # Metrics dashboard
│   │       └── void.html            # Infinite Void 3D experience (Three.js)
│   └── playback/                    # PlaybackThread (replay recordings)
├── tests/
│   ├── unit/                        # Calculator, classifier, smoother tests
│   └── integration/                 # OSCSink UDP test
└── .github/workflows/ci.yml         # GitHub Actions: test on 3.10 / 3.11 / 3.12
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Hands not detected | Improve lighting; keep hands within 50–150 cm of camera |
| High jitter | Switch smoother: `--smoother one_euro` (default); lower `--ema-alpha` if using EMA |
| No OSC in TouchDesigner | Confirm OSC In CHOP port = 7000; check Windows Firewall for localhost |
| Camera not opening | Try `--camera 1` or `--camera 2` |
| Low FPS | Reduce resolution: `--width 640 --height 480` |
| Module not found | Ensure venv is active and `pip install -e .` completed |
| `ValueError: list.remove(x)` in server.py | Update to latest code — fixed in `disconnect()` guard |
| Void page shows no hands | Run with `--dashboard` flag; click the page once to connect audio |
| Dashboard sound button missing | Hard-refresh the page (Ctrl+Shift+R) after updating |
| No sound in dashboard | Click **♪ SOUND OFF** first — browsers require a user gesture to start Web Audio |
| `--sound` flag errors | Install `sounddevice`: `pip install sounddevice` |
| Model download fails | Manually download `hand_landmarker.task` and place in `~/.hand_tracking_bridge/` |

---

## License

MIT
