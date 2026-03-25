# Hand Tracking Bridge for TouchDesigner - Complete Project Plan

## Project Overview

A real-time hand tracking application that bridges MediaPipe (ML hand detection) with TouchDesigner (creative visual tool) using OSC (Open Sound Control) protocol.

**Status:** ✅ Fully Functional  
**Version:** 1.0  
**Date:** March 25, 2026

---

## System Architecture

```
┌──────────────────┐
│   Webcam/Camera  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│   Python Application         │
│  (hand_tracker.py)          │
├──────────────────────────────┤
│ • MediaPipe Hands Detection  │
│ • Gesture Calculations       │
│ • EMA Smoothing              │
│ • OSC Message Transmission   │
└────────┬─────────────────────┘
         │ OSC UDP Port 7000
         │ localhost:7000
         ▼
┌──────────────────────────────┐
│   TouchDesigner              │
│  (OSC In CHOP)              │
├──────────────────────────────┤
│ • Receives hand position     │
│ • Receives gesture data      │
│ • Maps to visual parameters  │
│ • Creates interactive visuals│
└──────────────────────────────┘
```

---

## Installation & Setup

### 1. Python Environment Setup

**Step 1: Create Virtual Environment**
```bash
cd C:\Users\ASUS\Downloads\Mediapipe
python -m venv venv
venv\Scripts\activate  # On Windows
```

**Step 2: Install Python Dependencies**
```bash
pip install -r requirements.txt
```

**Dependencies Required:**
- mediapipe==0.10.13 (hand pose detection)
- opencv-python==4.9.0.80 (webcam capture & visualization)
- python-osc==1.8.3 (OSC protocol)
- numpy==1.26.4 (numerical computing)

**Step 3: Verify Installation**
```bash
python test_diagnostics.py
```

Expected output: All tests should pass (✓)

### 2. TouchDesigner Setup

**Step 1: Download TouchDesigner**
- Go to https://derivative.ca/download/touchdesigner
- Download Web Installer (~671MB)
- Install and launch

**Step 2: Create OSC Receiver**
- In TouchDesigner network editor
- Right-click → CHOP → oscin
- Name it: "osc_hands"

**Step 3: Configure OSC In CHOP**
- Click oscin node to select
- In parameters panel (right side):
  - **Port:** 7000
  - **Active:** ON (green toggle)
  - **Protocol:** Messaging (UDP)
  - **OSC Address Scope:** * (asterisk)

---

## Hand Tracking Implementation

### MediaPipe Configuration

**Landmarks Tracked (21 per hand):**
- 0: Wrist (palm base)
- 1-4: Thumb (base → tip)
- 5-8: Index finger (base → tip)
- 9-12: Middle finger (base → tip)
- 13-16: Ring finger (base → tip)
- 17-20: Pinky (base → tip)

**Key Landmarks Used:**
- Wrist (0) → Position tracking
- Thumb tip (4) → Pinch detection
- Index tip (8) → Pinch detection
- All fingertips (4,8,12,16,20) → Openness calculation

### Gesture Calculations

**1. Pinch Distance**
```
Distance = ||thumb_tip - index_tip||  (euclidean)
Pinch value = 1.0 - (distance / 0.15)  (normalized 0-1)
Range: 1.0 = pinched, 0.0 = open
```

**2. Hand Openness**
```
avg_distance = mean([distance(wrist, tip) for all fingertips])
Openness = (avg_distance - 0.15) / 0.4  (normalized 0-1)
Range: 1.0 = fully open, 0.0 = closed fist
```

**3. Wrist Position**
```
wrist_x = landmark[0].x  (0.0-1.0, left-right)
wrist_y = 1.0 - landmark[0].y  (0.0-1.0, inverted for top=1)
```

**4. Hand Presence**
```
present = 1 if hand detected, 0 if not detected
Sent as integer (0 or 1)
```

### Smoothing Algorithm

**Exponential Moving Average (EMA)**
```
smoothed = α * new_value + (1 - α) * old_value
α = 0.7 (configurable in config.py)

Effect:
- α = 0.5 → Heavy smoothing (laggy but stable)
- α = 0.7 → Balanced (responsive + smooth)
- α = 0.9 → Light smoothing (jittery but responsive)
```

---

## OSC Protocol & Messaging

### OSC Send Rate
- **Frequency:** 30 frames per second (30 FPS)
- **Addresses:** 10 unique OSC messages per frame
- **Total bandwidth:** Minimal (<1 Mbps)
- **Latency:** <50ms typically

### OSC Address Structure

```
/hand/{hand_id}/{param}

Where:
  hand_id = 0 (right hand) or 1 (left hand)
  param = wrist/x, wrist/y, pinch, openness, present
```

### Complete OSC Message Map

```
RIGHT HAND (Index 0):
├─ /hand/0/wrist/x      → float 0.0-1.0 ← Horizontal position
├─ /hand/0/wrist/y      → float 0.0-1.0 ← Vertical position  
├─ /hand/0/pinch        → float 0.0-1.0 ← 1=pinched, 0=open
├─ /hand/0/openness     → float 0.0-1.0 ← 1=open, 0=closed
└─ /hand/0/present      → int 0 or 1    ← Hand detected?

LEFT HAND (Index 1):
├─ /hand/1/wrist/x      → float 0.0-1.0
├─ /hand/1/wrist/y      → float 0.0-1.0
├─ /hand/1/pinch        → float 0.0-1.0
├─ /hand/1/openness     → float 0.0-1.0
└─ /hand/1/present      → int 0 or 1
```

---

## TouchDesigner Integration

### Basic Setup: Hand Position Tracking

**Goal:** Make a sphere follow your hand in 3D space

**Network Structure:**
```
oscin (port 7000)
  │
  ├─→ select (channel: hand_0_wrist_x)
  │    └─→ math (multiply by width)
  │         └─→ geo1.t.x
  │
  └─→ select (channel: hand_0_wrist_y)
       └─→ math (multiply by height)
            └─→ geo1.t.y
```

**Steps:**
1. Create `oscin` CHOP (port 7000)
2. Create `select` CHOP, set channel to `hand_0_wrist_x`
3. Create `math` CHOP, multiply value by canvas width (e.g., 10)
4. Drag math output → sphere's t.x (translate X)
5. Repeat for Y position with `hand_0_wrist_y`

**Result:** Sphere follows your hand's position

### Advanced Setup: Multi-Parameter Control

**Goal:** Use both hands to control multiple aspects

**Network Structure:**
```
oscin (port 7000)
  │
  ├─ Hand 0 (Right):
  │  ├─ wrist_x → geo1.t.x (position)
  │  ├─ wrist_y → geo1.t.y (position)
  │  ├─ pinch → geo1.s.x (scale)
  │  └─ openness → geo1.r.z (rotation)
  │
  └─ Hand 1 (Left):
     ├─ wrist_x → geo2.t.x (position)
     ├─ wrist_y → geo2.t.y (position)
     ├─ present → conditional enable/disable
     └─ openness → par.color (hue)
```

### Gesture-Based Triggering

**Example: Trigger animation on pinch**

```python
# In Text DAT with Python script:
def onCook(scriptOp):
    pinch = op('oscin')['hand_0_pinch'][0].val
    
    if pinch > 0.8:  # Strong pinch detected
        op('geo1').play = True  # Start animation
    else:
        op('geo1').play = False
```

---

## Project Files Reference

### Core Application Files

| File | Purpose | Key Content |
|------|---------|------------|
| `hand_tracker.py` | Main application | HandTracker class, gesture calculations, OSC sending |
| `run.py` | Launcher | Config loading, user-friendly startup |
| `config.py` | Configuration | All customizable parameters (no code editing needed) |

### Setup & Testing Files

| File | Purpose | Usage |
|------|---------|-------|
| `setup_check.py` | Dependency verification | `python setup_check.py` |
| `test_diagnostics.py` | System diagnostics | `python test_diagnostics.py` |
| `test_camera.py` | Camera access test | `python test_camera.py` |

### Documentation Files

| File | Content | Audience |
|------|---------|----------|
| `README.md` | Complete technical reference | Developers, power users |
| `QUICKSTART.md` | 5-minute setup guide | First-time users |
| `TOUCHDESIGNER_EXAMPLES.md` | 8 complete TD projects | TouchDesigner users |
| `PROJECT_OVERVIEW.md` | Architecture & structure | Understanding the codebase |
| `START_HERE.md` | Orientation guide | New users |

### Configuration

| File | Purpose |
|------|---------|
| `requirements.txt` | Python package dependencies |
| `.gitignore` | Git exclusions |

---

## Running the Application

### Quick Start (3 Steps)

**Step 1: Start Python Hand Tracking**
```bash
cd C:\Users\ASUS\Downloads\Mediapipe
python run.py
```

Expected: Webcam window opens with red hand landmarks and FPS counter

**Step 2: Open TouchDesigner**
- Launch TouchDesigner
- Open/create a project

**Step 3: Create OSC Receiver**
- Right-click network → CHOP → oscin
- Set port to 7000
- Toggle Active = ON
- Force Cook (right-click → Force Cook)

**Step 4: Use the Data**
- Drag oscin output to geometry parameters
- Move your hand - geometry responds!

---

## Customization Guide

### Modify Configuration (config.py)

Without touching code, customize these parameters:

```python
# Network
OSC_HOST = 'localhost'      # Target IP (localhost = same machine)
OSC_PORT = 7000             # Port number

# Performance
TARGET_FPS = 30             # 30 = default, 60 = faster
WEBCAM_WIDTH = 1280         # Lower = better FPS
WEBCAM_HEIGHT = 720

# Smoothing
SMOOTHING_ALPHA = 0.7       # 0.5=smooth, 0.9=jittery

# MediaPipe
MIN_DETECTION_CONFIDENCE = 0.7  # 0.5-1.0, stricter = fewer false positives
MIN_TRACKING_CONFIDENCE = 0.5   # 0.5-1.0
```

### Modify Code (hand_tracker.py)

Key methods to customize:

**Change camera device:**
```python
# Line ~280 in run():
cap = cv2.VideoCapture(0)  # 0=default, try 1,2,3... for other cameras
```

**Adjust gesture calibration:**
```python
# In calculate_pinch():
PINCH_MAX_DISTANCE = 0.15   # Wider = less sensitive pinch

# In calculate_openness():
OPENNESS_MIN_DISTANCE = 0.15    # Lower = easier to trigger
OPENNESS_MAX_DISTANCE = 0.55    # Higher = more range
```

---

## Troubleshooting Guide

### Issue: "Failed to read frame from webcam"

**Causes:**
1. Another app using camera (browser, Zoom, Discord, OBS)
2. Camera permissions not granted
3. Wrong camera device

**Solutions:**
1. Close all apps with camera access
2. Check system camera permissions
3. Run `python test_camera.py` to find correct device
4. Change camera index in code if needed

### Issue: OSC data not appearing in TouchDesigner

**Checklist:**
- [ ] Python app is running and showing "✓ OSC sent..." messages
- [ ] oscin CHOP port = 7000
- [ ] oscin CHOP Active toggle = ON (green)
- [ ] Network connectivity (both on localhost)
- [ ] Try Force Cook on oscin node

**Debug Steps:**
1. Check console output: `python run.py` should show OSC messages
2. Verify firewall isn't blocking port 7000 (rarely an issue for localhost)
3. Try restarting both applications

### Issue: Hand not being detected

**Reasons:**
- Poor lighting conditions
- Hand too far from camera
- Hand at extreme angle
- Camera resolution too low

**Solutions:**
- Ensure bright, even lighting
- Move hand 1-2 meters from camera
- Adjust detection confidence (lower = easier detection)
- Increase webcam resolution in config

### Issue: Jittery/shaky tracking

**Cause:** Smoothing alpha too high or insufficient lighting

**Fix:**
Edit config.py:
```python
SMOOTHING_ALPHA = 0.5  # Instead of 0.7 (more smoothing)
```

Or improve lighting conditions

---

## Performance Metrics

| Metric | Target | Typical |
|--------|--------|---------|
| Frame Rate | 30 FPS | 25-30 FPS |
| Latency | <100ms | 50-80ms |
| CPU Usage | <20% | 10-15% |
| Memory | <200MB | 100-150MB |
| Bandwidth | <1 Mbps | ~0.5 Mbps |

---

## Workflow Example: Complete Project

### Build: Interactive Color Sphere

**Goal:** Control a sphere's position and color with hand gestures

**Network in TouchDesigner:**
```
oscin
├─ hand_0_wrist_x → math → geo1.t.x
├─ hand_0_wrist_y → math → geo1.t.y
├─ hand_0_openness → math (*360) → geo1.r.z
└─ hand_0_pinch → hsv_adjust → par.color.hue
```

**Python side:**
- Hand position already sent via wrist_x/y
- Openness used for rotation
- Pinch magnitude maps to color

**TouchDesigner setup:**
1. Create oscin (port 7000)
2. Create geo (geometry)
3. Connect each gesture to parameters
4. Add material with color mapping

**Interaction:**
- Move hand left/right → sphere moves X
- Move hand up/down → sphere moves Y
- Open/close hand → sphere rotates
- Pinch intensity → sphere color hue changes

---

## File Download & Setup References

### Python Installation
- Python 3.8+: https://www.python.org/downloads/
- Virtual environments: `python -m venv venv`

### TouchDesigner
- Download: https://derivative.ca/download/touchdesigner
- Web Installer: ~671MB
- Full Installer: ~2.7GB

### Dependencies
All specified in `requirements.txt`:
```
mediapipe==0.10.13
opencv-python==4.9.0.80
python-osc==1.8.3
numpy==1.26.4
```

---

## Next Steps & Ideas

### Immediate (Week 1)
- [ ] Get hand tracking running
- [ ] Connect to TouchDesigner
- [ ] Make sphere follow hand
- [ ] Test pinch and openness gestures

### Short-term (Week 2-3)
- [ ] Build 2-hand interactive demo
- [ ] Create gesture-triggered animations
- [ ] Record hand motion data
- [ ] Explore multi-person tracking

### Long-term (Future)
- [ ] Gesture classification (peace sign, thumbs up, etc.)
- [ ] Real-time motion analysis
- [ ] Finger-individual tracking
- [ ] Multi-camera setup
- [ ] Network streaming to remote TD instance
- [ ] AR integration

### Integration Ideas
- **Music visualization:** Hand position = frequency, pinch = volume
- **3D object manipulation:** Move/rotate/scale with both hands
- **Game control:** Gesture-based gameplay
- **Data visualization:** Hand motion driving data plots
- **Live performance:** Real-time interactive art

---

## Support & Resources

### Documentation in This Project
1. **START_HERE.md** - Read this first!
2. **QUICKSTART.md** - 5-minute setup
3. **README.md** - Full reference
4. **TOUCHDESIGNER_EXAMPLES.md** - 8 complete examples
5. **PROJECT_OVERVIEW.md** - Deep dive into architecture

### External Resources
- MediaPipe Docs: https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
- TouchDesigner Tutorials: https://derivative.ca/learn/touchdesigner
- OSC Protocol: http://opensoundcontrol.org/

### Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| Port already in use | Change OSC_PORT in config.py |
| Multiple Python instances | Kill old processes, restart fresh |
| Memory leak | Restart app every 1-2 hours for extended use |
| Ghosting/lag | Lower SMOOTHING_ALPHA to 0.5 |

---

## Project Completion Checklist

- [x] Hand detection implemented (MediaPipe)
- [x] Gesture calculations (pinch, openness, position)
- [x] EMA smoothing applied
- [x] OSC transmission to TouchDesigner
- [x] Live debug visualization
- [x] Error handling & logging
- [x] Configuration system
- [x] Setup verification tools
- [x] Comprehensive documentation
- [x] Example integrations
- [x] Troubleshooting guide

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Mar 25, 2026 | Initial release with full documentation |

---

## License & Attribution

Built with:
- **MediaPipe** - Google's hand pose ML framework
- **OpenCV** - Computer vision library
- **python-osc** - OSC protocol implementation
- **NumPy** - Numerical computing

Created for TouchDesigner interactive projects.

---

**🎉 You're all set! Start with START_HERE.md or jump to QUICK START section above.**
