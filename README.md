# Hand Tracking Bridge for TouchDesigner

A real-time hand tracking application that bridges MediaPipe with TouchDesigner using the OSC protocol. Tracks hand landmarks, calculates gesture metrics, and sends normalized values to TouchDesigner in real-time.

## Features

- **Real-time Hand Detection**: Detects up to 2 hands simultaneously using MediaPipe
- **Gesture Calculations**:
  - Pinch distance (thumb to index finger)
  - Hand openness (average fingertip distance from wrist)
  - Wrist position (normalized X, Y coordinates)
  - Hand presence detection
- **OSC Protocol**: Sends data to TouchDesigner via UDP on port 7000
- **Smoothing**: Exponential Moving Average (EMA) smoothing with α=0.7 to reduce jitter
- **Live Debug Visualization**: OpenCV window showing landmarks, gesture values, and FPS
- **Performance**: Targets 30 FPS with frame rate control

## Installation

### Prerequisites
- Python 3.8 or higher
- Webcam

### Setup Steps

1. **Clone/Navigate to project directory**:
   ```bash
   cd path/to/Mediapipe
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # or
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
python hand_tracker.py
```

The application will:
1. Open your webcam
2. Display a live feed with hand landmarks and gesture values
3. Send OSC messages to localhost:7000
4. Press 'q' to quit gracefully

### TouchDesigner Integration

#### Setup in TouchDesigner:

1. **Create OSC In CHOP**:
   - Add an `oscin` CHOP to your network
   - Set the **Port** to `7000`
   - Set the **Active** to toggle input on/off

2. **Auto-Created Channels**:
   The OSC In CHOP will automatically create channels for:
   ```
   /hand/0/wrist/x         → Hand 0 wrist X (0.0-1.0)
   /hand/0/wrist/y         → Hand 0 wrist Y (0.0-1.0)
   /hand/0/pinch           → Hand 0 pinch value (0.0-1.0)
   /hand/0/openness        → Hand 0 openness (0.0-1.0)
   /hand/0/present         → Hand 0 detected (1=yes, 0=no)
   /hand/1/wrist/x         → Hand 1 wrist X
   /hand/1/wrist/y         → Hand 1 wrist Y
   /hand/1/pinch           → Hand 1 pinch value
   /hand/1/openness        → Hand 1 openness
   /hand/1/present         → Hand 1 detected
   ```

3. **Extract Specific Channels**:
   Use a `select` CHOP to isolate channels:
   ```
   select CHOP → channel: hand_0_wrist_x
   ```

4. **Normalize and Map Values**:
   Use `math` CHOP for range remapping:
   - For values already 0-1: pass through
   - For positioning: multiply by target range
   - For presence: convert to boolean logic (>0.5)

5. **Example Setup Chain**:
   ```
   oscin → select (hand_0_wrist_x) → math (multiply by width) → null
                                  ↓
                              (use for X position)
   ```

## OSC Address Structure

All OSC messages are floats unless specified as integers:

| Address | Type | Range | Description |
|---------|------|-------|-------------|
| `/hand/0/wrist/x` | float | 0.0-1.0 | Right hand wrist horizontal position |
| `/hand/0/wrist/y` | float | 0.0-1.0 | Right hand wrist vertical position |
| `/hand/0/pinch` | float | 0.0-1.0 | Right hand pinch intensity (1=pinched, 0=open) |
| `/hand/0/openness` | float | 0.0-1.0 | Right hand openness (1=fully open, 0=closed) |
| `/hand/0/present` | int | 0 or 1 | Right hand detected? |
| `/hand/1/wrist/x` | float | 0.0-1.0 | Left hand wrist horizontal position |
| `/hand/1/wrist/y` | float | 0.0-1.0 | Left hand wrist vertical position |
| `/hand/1/pinch` | float | 0.0-1.0 | Left hand pinch intensity |
| `/hand/1/openness` | float | 0.0-1.0 | Left hand openness |
| `/hand/1/present` | int | 0 or 1 | Left hand detected? |

## Gesture Calculations

### Pinch Distance
- Measures euclidean distance between thumb tip (landmark 4) and index finger tip (landmark 8)
- Normalized: 1.0 = fully pinched, 0.0 = open
- Inverted: 1.0 - (distance / max_distance)

### Hand Openness
- Average distance of all 5 fingertips (landmarks 4, 8, 12, 16, 20) from wrist (landmark 0)
- Normalized: 1.0 = fully open hand, 0.0 = closed fist
- Formula: (avg_distance - 0.15) / 0.4, clipped to 0.0-1.0

### Wrist Position
- Direct X, Y coordinates from wrist landmark
- Normalized to 0.0-1.0 (camera frame dimensions)
- Y is inverted (top of frame = 1.0, bottom = 0.0)

## Smoothing

All values are smoothed using exponential moving average (EMA):
```
smoothed_value = α * new_value + (1 - α) * previous_value
where α = 0.7
```

This reduces jitter while maintaining responsiveness.

## Landmark Reference

MediaPipe Hands uses 21 landmarks per hand:

```
Landmark Index → Body Part
0  → Wrist
1-4   → Thumb (base to tip)
5-8   → Index (base to tip)
9-12  → Middle (base to tip)
13-16 → Ring (base to tip)
17-20 → Pinky (base to tip)
```

Key landmarks used in this application:
- **0** = Wrist
- **4** = Thumb tip
- **8** = Index tip
- **12** = Middle tip
- **16** = Ring tip
- **20** = Pinky tip

## Troubleshooting

### No OSC messages being received in TouchDesigner
- Verify the OSC In CHOP port is set to `7000`
- Check that the Python app shows "OSC client initialized" in logs
- Ensure firewall isn't blocking localhost:7000
- Look for "OSC messages sent" in the debug overlay

### Hands not being detected
- Ensure good lighting
- Keep hands within frame and in front of camera
- Try moving closer to camera (within 1-2 meters)
- Check webcam permissions

### High jitter in values
- The smoothing is set to α=0.7 for responsiveness
- To reduce jitter more, modify `self.alpha` in `hand_tracker.py` (lower value = more smoothing)
- Example: `self.alpha = 0.5` for heavier smoothing

### Low FPS
- Reduce webcam resolution in `cap.set()` calls
- Check CPU usage (MediaPipe is GPU-accelerated on some systems)
- Disable debug visualization temporarily
- Close other applications

## Performance Notes

- Targets 30 FPS on standard hardware
- MediaPipe Hands detection is optimized for real-time use
- Frame rate is controlled to maintain consistent 30 FPS
- All values are transmitted every frame to OSC

## Code Structure

```
hand_tracker.py
├── HandTracker class
│   ├── __init__()              → Setup MediaPipe and OSC
│   ├── process_frame()         → Detect landmarks and calculate gestures
│   ├── calculate_pinch()       → Compute pinch distance
│   ├── calculate_openness()    → Compute hand openness
│   ├── smooth_value()          → Apply EMA smoothing
│   ├── send_osc()              → Transmit OSC messages
│   ├── _draw_debug_info()      → Render debug window
│   └── run()                   → Main event loop
└── main()                       → Entry point
```

## Dependencies

- **mediapipe** (0.10.9): Hand pose estimation
- **opencv-python** (4.9.0.80): Webcam capture and visualization
- **python-osc** (1.8.3): OSC protocol client
- **numpy** (1.26.4): Numerical computations

## License

Created for TouchDesigner real-time hand tracking applications.

## Advanced Usage

### Custom OSC Host/Port
```python
tracker = HandTracker(osc_host='192.168.1.100', osc_port=9000)
tracker.run()
```

### Custom Target FPS
```python
tracker.run(target_fps=60)  # Run at 60 FPS instead of 30
```

### Adjusting Smoothing
Modify the `self.alpha` value in `HandTracker.__init__()`:
- Lower values (0.3-0.5): More smoothing, less responsive
- Higher values (0.7-0.9): Less smoothing, more responsive

### Single Hand Mode
Comment out or modify the hand detection loop in `process_frame()` to track only the primary hand.
