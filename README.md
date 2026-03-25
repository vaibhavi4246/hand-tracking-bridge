# Hand Tracking Bridge

A real-time hand gesture pipeline that bridges MediaPipe hand tracking with TouchDesigner, web browsers, and any OSC-compatible software.

**V2** — refactored from a single-file script into a production-grade multi-threaded pipeline with a plugin output architecture, advanced gesture recognition, a live web dashboard, per-user calibration, and a full CI-backed test suite.

---

## Features

| Category | Capability |
|----------|-----------|
| **Detection** | Up to 2 hands @ 30 FPS via MediaPipe |
| **Gestures** | Pinch, openness, per-finger flexion (0–1), palm orientation (roll/pitch/yaw), wrist velocity & acceleration |
| **Classification** | Discrete gestures: `fist`, `open`, `peace`, `thumbs_up`, `pointing` with temporal hysteresis |
| **Smoothing** | One Euro Filter (adaptive, low-latency) + EMA |
| **Output** | OSC (TouchDesigner), WebSocket (browser), JSONL recording |
| **Dashboard** | Live web UI at `localhost:8000` — skeleton canvas, gesture bars, FPS/latency |
| **Calibration** | Per-user profiles with auto-calibration (5th/95th percentile) |
| **Playback** | Replay recordings without webcam — great for TD patch development |
| **Tests** | pytest unit + integration tests, GitHub Actions CI on Python 3.10–3.12 |

---

## Installation

Requires **Python 3.10+** and a webcam.

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

---

## Quick Start

```bash
# Basic — OSC to TouchDesigner on port 7000
hand-tracker

# With live web dashboard at http://localhost:8000
hand-tracker --dashboard --ws

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
InferenceThread  ←── MediaPipe + GestureCalculator + OneEuroFilter + GestureClassifier
  │
  ▼ (gesture_queue)
DispatcherThread ──► OSCSink       → TouchDesigner (UDP:7000)
                ──► WebSocketSink  → Browser dashboard (WS:8765)
                ──► FileSink       → JSONL recording

Main thread: OpenCV visualization window
```

Key design decisions:

- **Bounded queues + frame-drop policy** — system always operates on the most recent frame; slow inference never builds latency backlog
- **Frozen dataclasses (`GestureFrame`)** — immutable across thread boundaries, no locks needed
- **Pure functions in `calculator.py`** — no state, fully testable without mocking
- **`OutputSink` ABC** — adding MIDI/DMX output requires zero pipeline changes (Open/Closed Principle)
- **One Euro Filter** over EMA — adapts smoothing cutoff to signal velocity (Casiez et al., CHI 2012)

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
│   ├── sinks/                       # OSCSink, WebSocketSink, FileSink
│   ├── calibration/                 # AutoCalibrator + profiles
│   ├── dashboard/                   # FastAPI server + vanilla JS frontend
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

---

## License

MIT
