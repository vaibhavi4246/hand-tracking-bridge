# Hand Tracking Bridge

A real-time hand gesture pipeline that bridges MediaPipe hand tracking with TouchDesigner, web browsers, and any OSC-compatible software.

**V2** — refactored from a single-file script into a production-grade multi-threaded pipeline with a plugin output architecture, advanced gesture recognition, a live web dashboard, an infinite-void 3D interactive experience, per-user calibration, and a full CI-backed test suite.

---

## Features

| Category | Capability |
|----------|-----------|
| **Detection** | Up to 2 hands @ 30 FPS via MediaPipe Tasks API |
| **Gestures** | Pinch, openness, per-finger flexion (0–1), palm orientation (roll/pitch/yaw), wrist velocity & acceleration |
| **Classification** | Discrete gestures: `fist`, `open`, `peace`, `thumbs_up`, `pointing` with temporal hysteresis |
| **Smoothing** | One Euro Filter (adaptive, low-latency) + EMA |
| **Output** | OSC (TouchDesigner), WebSocket (browser), JSONL recording |
| **Dashboard** | Live metrics UI at `localhost:8000` — skeleton canvas, gesture bars, FPS/latency |
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

## Infinite Void — 3D Interactive Experience

Open **http://localhost:8000/void** while `hand-tracker --dashboard` is running.

Click the screen once to unlock audio, then show your hands to the camera.

### Hand Controls

| Action | Effect |
|--------|--------|
| Move wrist | Glowing cursor follows your hand in 3D space |
| **Pinch** (thumb + index) | Grab the nearest floating object |
| Move while pinching | Drag the object anywhere |
| **Tilt palm** | Rotates the grabbed object (roll / pitch / yaw) |
| **Openness** | Scales the grabbed object |
| **Release pinch with velocity** | Throw / fling the object |
| **Fist** ✊ | Spawn a new glowing 3D shape at your hand |
| **Open palm** 🖐 | Explode nearby objects outward |
| **Two hands** | Distance between wrists scales the grabbed object |

### Sound

- Hand height → pitch (lower hand = bass, 80–800 Hz)
- Openness → filter brightness (closed = dark, open = bright)
- Pinch → volume (louder when gripping)
- Spawning / exploding → synthesized sound effects
- Ambient drone activates when hands are detected

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
│   ├── sinks/                       # OSCSink, WebSocketSink, FileSink, DashboardSink
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
| Void page shows no hands | Run with `--dashboard` flag; click the page once to connect audio |
| Model download fails | Manually download `hand_landmarker.task` and place in `~/.hand_tracking_bridge/` |

---

## License

MIT
