# Hand Tracking Bridge - Project Overview

A complete Python application for real-time hand tracking via MediaPipe with OSC protocol output to TouchDesigner.

## Project Summary

This application captures video from your webcam, detects hand landmarks using Google's MediaPipe library, calculates gesture metrics (pinch, openness), and sends the data via OSC protocol to TouchDesigner for real-time interactive control.

**Status:** ✅ Complete and Ready to Use

**Target:** TouchDesigner artists, interactive media designers, motion capture enthusiasts

---

## File Structure

```
Mediapipe/
├── hand_tracker.py              # Main application (core logic)
├── run.py                       # Quick-start launcher
├── config.py                    # Configuration parameters
├── setup_check.py               # Installation verification
├── test_diagnostics.py          # Diagnostic tests
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git exclusions
├── README.md                    # Full documentation
├── QUICKSTART.md               # 5-minute setup guide
├── TOUCHDESIGNER_EXAMPLES.md   # Integration examples
└── PROJECT_OVERVIEW.md         # This file
```

---

## Files Description

### Core Application Files

#### `hand_tracker.py` (main file)
**Purpose:** Complete hand tracking implementation
**Contents:**
- `HandTracker` class (all gesture detection logic)
- MediaPipe initialization and configuration
- OSC client setup
- Frame processing pipeline
- Gesture calculations (pinch, openness)
- EMA smoothing implementation
- Debug visualization
- Main event loop

**Key Methods:**
- `__init__()` - Setup MediaPipe and OSC
- `process_frame()` - Detect landmarks
- `calculate_pinch()` - Real-time pinch metric
- `calculate_openness()` - Hand openness metric
- `smooth_value()` - EMA smoothing
- `send_osc()` - OSC transmission
- `run()` - Main loop with webcam capture

**Usage:** `python hand_tracker.py` or `python run.py`

---

#### `run.py` (launcher)
**Purpose:** User-friendly application launcher
**Contents:**
- Imports configuration from `config.py`
- Initializes HandTracker with config values
- Provides console feedback during startup
- Handles keyboard interrupts gracefully

**Usage:** `python run.py`

---

#### `config.py` (configuration)
**Purpose:** Centralized configuration management
**Configurable Parameters:**
- OSC host/port (default: localhost:7000)
- MediaPipe confidence thresholds
- Target FPS (default: 30)
- Webcam resolution (1280x720)
- Smoothing alpha value (0.7)
- Gesture calibration values
- Debug visualization settings
- Logging configuration

**Usage:** Edit values, save, and restart `run.py`

---

### Setup & Testing Files

#### `requirements.txt`
**Purpose:** Python package dependencies
**Packages:**
- mediapipe==0.10.9 (hand pose ml)
- opencv-python==4.9.0.80 (webcam/visualization)
- python-osc==1.8.3 (OSC protocol)
- numpy==1.26.4 (numerical computing)

**Usage:** `pip install -r requirements.txt`

---

#### `setup_check.py`
**Purpose:** Verify installation and system setup
**Checks:**
- Python version (3.8+)
- pip availability
- Package imports
- Webcam accessibility

**Usage:** `python setup_check.py`

---

#### `test_diagnostics.py`
**Purpose:** Comprehensive diagnostic testing
**Tests:**
- NumPy functionality
- OpenCV and webcam access
- MediaPipe initialization
- Gesture calculations
- OSC connectivity

**Usage:** `python test_diagnostics.py`

**Output:** Detailed report with ✓/❌ for each test

---

### Documentation Files

#### `README.md` (full documentation)
**Sections:**
- Installation setup
- Usage instructions
- TouchDesigner integration guide
- OSC address structure reference
- Gesture calculation formulas
- Landmark reference (21 points)
- Troubleshooting guide
- Performance notes
- Code structure explanation
- Advanced usage examples

**Best for:** Complete reference, detailed explanations

---

#### `QUICKSTART.md` (5-minute guide)
**Sections:**
- 5-minute setup walkthrough
- Quick configuration edit
- Troubleshooting table
- What's sending to TouchDesigner (channel names)
- Common first project example

**Best for:** Getting started quickly, overview

---

#### `TOUCHDESIGNER_EXAMPLES.md` (integration examples)
**Sections:**
- 8 complete example projects:
  1. Hand position tracking
  2. Pinch-to-scale control
  3. Openness to rotation
  4. Two-hand control
  5. Hand presence detection
  6. Gesture-based animation trigger
  7. Multi-parameter mapping
  8. Debug monitor

- Implementation details for each
- Python script examples
- Network setup diagrams
- Tips & tricks
- Performance notes

**Best for:** Building TouchDesigner projects

---

#### `PROJECT_OVERVIEW.md` (this file)
**Purpose:** High-level project summary and file guide

---

### Git File

#### `.gitignore`
**Purpose:** Exclude unnecessary files from version control
**Ignores:**
- Python cache (`__pycache__`, `*.pyc`)
- Virtual environments (`venv/`, `env/`)
- IDE files (`.vscode/`, `.idea/`)
- Logs and backups
- OS files

---

## Quick Start Paths

### For Impatient Users (5 min)
```bash
pip install -r requirements.txt
python run.py
# Then in TouchDesigner: OSC In CHOP on port 7000
```

### For Careful Users (10 min)
```bash
python setup_check.py          # Verify dependencies
python test_diagnostics.py     # Test everything
python run.py                  # Launch app
```

### For TouchDesigner Integration
1. Follow QUICKSTART.md for app setup
2. Check TOUCHDESIGNER_EXAMPLES.md for integration patterns
3. Use Example 1 or 8 for debugging

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Webcam/Camera                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
          ┌────────────────────────────┐
          │   OpenCV Cap / cv2.read()  │
          └────────────┬───────────────┘
                       │
                       ▼
          ┌────────────────────────────┐
          │  MediaPipe Hand Detection  │
          │  (21 landmarks per hand)   │
          └────────────┬───────────────┘
                       │
                       ▼
          ┌────────────────────────────────────────┐
          │  Gesture Calculations:                 │
          │  - Pinch (thumb-index distance)       │
          │  - Openness (fingertip avg distance)  │
          │  - Wrist X/Y (normalized 0-1)         │
          │  - Hand presence (detected?)           │
          └────────────┬─────────────────────────┘
                       │
              ┌────────┴─────────┐
              │                  │
              ▼                  ▼
     ┌──────────────────┐  ┌──────────────────┐
     │ EMA Smoothing    │  │ Debug Viz (OpenCV│
     │ (α=0.7)          │  │ - Landmarks      │
     │ (reduce jitter)  │  │ - Values overlay │
     └────────┬─────────┘  │ - FPS counter)   │
              │            └────────┬─────────┘
              │                     │
              └────────┬────────────┘
                       │
                       ▼
          ┌────────────────────────────┐
          │  OSC Client (pythonosc)    │
          │  UDP to localhost:7000     │
          └────────────┬───────────────┘
                       │
                       ▼
          ┌────────────────────────────┐
          │  /hand/0/wrist/x   (float) │
          │  /hand/0/wrist/y   (float) │
          │  /hand/0/pinch     (float) │
          │  /hand/0/openness  (float) │
          │  /hand/0/present   (int)   │
          │  /hand/1/...       (...)   │
          │  (same for hand 1)         │
          └────────────┬───────────────┘
                       │
                       ▼
          ┌────────────────────────────┐
          │  TouchDesigner (OSC In)    │
          │  Port 7000                 │
          └────────────────────────────┘
```

---

## Data Flow

### Per Frame (30 times per second):
1. **Capture** - Read frame from webcam (1280×720)
2. **Process** - Run MediaPipe hand detection (~30 landmarks per hand)
3. **Calculate** - Compute pinch and openness gestures
4. **Smooth** - Apply EMA smoothing (α=0.7)
5. **Visualize** - Draw landmarks and metrics on frame
6. **Send** - Transmit 10 OSC values (per hand)
7. **Display** - Show annotated frame in debug window

### Performance:
- Processing: ~15-20ms MediaPipe
- OSC Send: <1ms
- Display: ~5-8ms
- **Total: ~30ms (30 FPS)**

---

## Configuration Options

### Modify `config.py` to customize:

```python
# Network
OSC_HOST = 'localhost'              # Change to remote IP
OSC_PORT = 7000                     # Change if port conflicts

# Performance
TARGET_FPS = 30                     # 60 for faster, 15 for slower
WEBCAM_WIDTH = 1280                 # Lower for better performance
WEBCAM_HEIGHT = 720

# Gesture
SMOOTHING_ALPHA = 0.7               # 0.5=smooth, 0.9=jittery
PINCH_MAX_DISTANCE = 0.15           # Adjust calibration
OPENNESS_MIN_DISTANCE = 0.15        # Adjust calibration
OPENNESS_MAX_DISTANCE = 0.55        # Adjust calibration

# MediaPipe
MIN_DETECTION_CONFIDENCE = 0.7      # Stricter detection
MIN_TRACKING_CONFIDENCE = 0.5       # Stricter tracking
```

---

## Features Implemented ✅

- [x] Real-time hand detection (up to 2 hands)
- [x] 21 landmark detection per hand
- [x] Pinch gesture calculation
- [x] Hand openness calculation
- [x] Wrist position tracking (normalized)
- [x] Hand presence detection
- [x] EMA smoothing (α=0.7)
- [x] OSC protocol transmission
- [x] 30 FPS target performance
- [x] Live debug visualization
- [x] Graceful error handling
- [x] Comprehensive logging
- [x] Configuration management
- [x] Setup verification tools
- [x] Diagnostic testing suite
- [x] TouchDesigner integration examples

---

## System Requirements

### Hardware (minimum):
- 1 GHz processor
- 2 GB RAM
- USB webcam or built-in camera

### Hardware (recommended):
- 2+ GHz processor
- 4+ GB RAM
- Good quality webcam
- Decent lighting

### Software:
- Python 3.8+
- Windows/macOS/Linux
- pip package manager

---

## Known Limitations

1. **Distance-based calibration:** Pinch/openness values are calibrated for roughly 50cm hand distance from camera. Adjust in config if needed.

2. **Single camera:** Currently expects device 0 (default camera). To use different camera, modify: `cv2.VideoCapture(1)` or `(2)`

3. **Occlusion:** Hand detection can fail if hands are heavily occluded or crossed.

4. **Lighting:** Low-light environments reduce detection quality. Better lighting = better results.

5. **Network:** OSC currently localhost only. For remote, change `OSC_HOST` in config.py to target IP.

---

## Future Enhancement Ideas

- [ ] Multi-window OSC output (multiple TD instances)
- [ ] Gesture classification (peace sign, thumbs up, etc.)
- [ ] Hand skeleton bone length tracking
- [ ] Palm motion/velocity calculation
- [ ] Finger individual flexion metrics
- [ ] GPU acceleration options
- [ ] Recording/playback functionality
- [ ] Network streaming mode
- [ ] Gesture recording library

---

## Troubleshooting Checklist

**Application won't start:**
- [ ] Run `python test_diagnostics.py`
- [ ] Verify all tests pass
- [ ] Check Python 3.8+

**No hands detected:**
- [ ] Check lighting (bright room?)
- [ ] Move closer to camera (1-2 meters)
- [ ] Clean camera lens
- [ ] Verify webcam works (`python test_diagnostics.py`)

**OSC not reaching TouchDesigner:**
- [ ] Check OSC In CHOP port = 7000
- [ ] Toggle "Active" ON in OSC In CHOP
- [ ] Verify Python app running (`python run.py`)
- [ ] Check firewall (localhost should work)
- [ ] Monitor packets with network tool

**Jerky/jittery movement:**
- [ ] Lower SMOOTHING_ALPHA in config.py (try 0.5)
- [ ] Increase lighting
- [ ] Move steadily and slowly

**Low FPS:**
- [ ] Close other applications
- [ ] Reduce webcam resolution in config
- [ ] Lower detection confidence thresholds
- [ ] Check CPU usage

---

## Support & Issues

For problems:
1. Run `test_diagnostics.py` to identify issue
2. Check relevant section in README.md
3. Review TOUCHDESIGNER_EXAMPLES.md if TouchDesigner related
4. Adjust config.py parameters
5. Check console logs for error messages

---

## License & Credits

Built with:
- **MediaPipe** - Google's hand pose framework
- **OpenCV** - Computer vision library
- **python-osc** - OSC protocol implementation
- **NumPy** - Numerical computing

---

## Getting Help

### In Each File:
- `hand_tracker.py` - Docstrings explain each method
- `config.py` - Comments explain each parameter
- `README.md` - Detailed technical reference
- `QUICKSTART.md` - Quick 5-minute overview
- `TOUCHDESIGNER_EXAMPLES.md` - Real-world TD examples
- `test_diagnostics.py` - Checks what's working/broken

---

## Next Steps

1. **Run:** `python run.py`
2. **Monitor:** Check debug window for landmarks
3. **Connect:** Set up OSC In CHOP in TouchDesigner
4. **Integrate:** Follow TOUCHDESIGNER_EXAMPLES.md
5. **Create:** Build your interactive project!

---

Created with ❤️ for TouchDesigner artists
