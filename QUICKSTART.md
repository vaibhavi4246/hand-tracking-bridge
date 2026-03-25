# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies (2 minutes)
```bash
cd path/to/Mediapipe
pip install -r requirements.txt
```

### 2. Verify Setup (1 minute)
```bash
python test_diagnostics.py
```
Look for "✓ All tests passed!" - if you see this, you're good to go!

### 3. Start Application (2 minutes)
```bash
python run.py
```

You should see:
- A webcam window titled "Hand Tracking - OSC Bridge"
- Your hands drawn with MediaPipe landmark points
- Live gesture values (pinch, openness) displayed
- FPS counter in top-left corner

### 4. Basic TouchDesigner Setup

In TouchDesigner:
```
1. Create → CHOP → oscinchop
2. Rename to "osc_hands"
3. In properties:
   - Port: 7000
   - Active: toggle ON
4. Click "Reload"
```

You should now see channels auto-create as OSC messages arrive.

---

## Quick Configuration

Edit `config.py` to customize:

```python
# Change OSC port
OSC_PORT = 9000

# Change target FPS
TARGET_FPS = 60

# Smoother tracking (less responsive)
SMOOTHING_ALPHA = 0.5

# Faster tracking (more jittery)
SMOOTHING_ALPHA = 0.9
```

Then restart with: `python run.py`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Webcam not found" | Check camera permissions, try `VideoCapture(1)` if multiple cameras |
| No OSC in TouchDesigner | Verify port 7000 in OSC In CHOP, check firewall |
| Shaky tracking | Lower `SMOOTHING_ALPHA` in `config.py` |
| Low FPS | Close other apps, reduce `WEBCAM_WIDTH`/`HEIGHT` in config |
| Hand detection fails | Better lighting, move closer to camera |

---

## What's Sending to TouchDesigner?

Every frame, these values are sent to 7000:

**Right Hand (index 0):**
- `/hand/0/wrist/x` → 0.0-1.0 (left-right)
- `/hand/0/wrist/y` → 0.0-1.0 (top-bottom)
- `/hand/0/pinch` → 0.0-1.0 (1=pinched)
- `/hand/0/openness` → 0.0-1.0 (1=open)
- `/hand/0/present` → 0 or 1 (detected?)

**Left Hand (index 1):**
- `/hand/1/wrist/x` → 0.0-1.0
- `/hand/1/wrist/y` → 0.0-1.0
- `/hand/1/pinch` → 0.0-1.0
- `/hand/1/openness` → 0.0-1.0
- `/hand/1/present` → 0 or 1

---

## Next Steps

1. ✓ Verify setup runs (`python run.py`)
2. ✓ Connect to TouchDesigner OSC In CHOP
3. ✓ Use Select CHOPs to isolate channels
4. ✓ Map to visual parameters with Math CHOPs
5. ✓ Build your interactive project!

---

## Common First Project

**Make a sphere follow your hand position:**

```
OSC In CHOP (port 7000)
  ↓
select (select hand_0_wrist_x and hand_0_wrist_y)
  ↓
Multiply by canvas size
  ↓
Connect to geometry translate X, Y
```

That's it! Your sphere follows your hand.

---

For full documentation, see `README.md`
