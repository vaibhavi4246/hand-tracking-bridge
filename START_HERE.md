# 🚀 Hand Tracking Bridge - START HERE

Welcome! Your complete hand tracking application is ready. Here's what you have:

## ✅ What Was Built

A production-ready Python application that:
- ✓ Tracks hands in real-time via webcam using MediaPipe
- ✓ Calculates pinch, openness, and wrist position gestures  
- ✓ Sends OSC messages to TouchDesigner at 30 FPS
- ✓ Includes smooth, responsive tracking with jitter reduction
- ✓ Provides live debug visualization with landmarks and metrics
- ✓ Handles errors gracefully with comprehensive logging

## 📋 Files Created (11 total)

### Application Files (Use These)
- **`run.py`** ← **START HERE** - Quick launcher with config
- `hand_tracker.py` - Complete implementation (well-documented)
- `config.py` - Easy configuration without code edits

### Setup & Validation
- `setup_check.py` - Verify Python dependencies installed
- `test_diagnostics.py` - Test all components before running
- `requirements.txt` - All Python packages needed

### Documentation (Your Reference)
- `QUICKSTART.md` - 5-minute setup guide (read this first)
- `README.md` - Full technical documentation
- `TOUCHDESIGNER_EXAMPLES.md` - 8 complete TD examples
- `PROJECT_OVERVIEW.md` - Architecture & file guide
- `.gitignore` - Git configuration

---

## 🏃 Three Ways to Get Started

### Option 1: Ultra-Fast (5 minutes)
```bash
pip install -r requirements.txt
python run.py
```
Then in TouchDesigner: Add oscin CHOP, set port 7000. Done!

### Option 2: Safe (10 minutes)  
```bash
python setup_check.py          # Install packages interactively
python test_diagnostics.py     # Verify everything works
python run.py                  # Launch application
```

### Option 3: Step-by-Step (Read First)
1. Read `QUICKSTART.md` (5 min)
2. Run `python setup_check.py` (2 min)
3. Run `python test_diagnostics.py` (2 min)
4. Run `python run.py` (ongoing)
5. Check `TOUCHDESIGNER_EXAMPLES.md` for integration

---

## 🎯 What Happens When You Run It

```
$ python run.py

Hand Tracking Bridge for TouchDesigner
======================================

📋 Configuration:
   OSC Target: localhost:7000
   Target FPS: 30
   Webcam Resolution: 1280x720
   Smoothing Alpha: 0.7
   Detection Confidence: 0.7

🎥 Starting hand tracking...
   Press 'q' or close window to quit
```

A window opens showing:
- Your webcam feed
- Hand landmark dots and connections
- Real-time pinch and openness values
- FPS counter (should show 30 FPS)

Meanwhile, OSC messages stream to port 7000 for TouchDesigner.

---

## 🎮 Quick Test in TouchDesigner

1. **Create oscin CHOP:**
   ```
   Create → CHOP → oscin
   ```

2. **Configure it:**
   - Set Port to: `7000`
   - Toggle "Active" ON
   - Click "Reload"

3. **Watch channels appear:**
   - hand_0_wrist_x
   - hand_0_wrist_y  
   - hand_0_pinch
   - hand_0_openness
   - hand_0_present
   - (same for hand_1)

4. **Make sphere follow hand** (tutorial):
   ```
   oscin
   └─ select (hand_0_wrist_x)
        └─ multiply by width
             └─ geo1.t.x (translate)
   ```

Boom! Your sphere follows your hand. ✨

---

## 🔧 If Something Doesn't Work

### Python Won't Start?
```bash
python setup_check.py
```
This will tell you exactly what's missing.

### Packages Not Installed?
```bash
pip install -r requirements.txt
```

### Hands Not Detected?
- Better lighting (bright room)
- Move closer to camera (1-2 meters)
- Check webcam works: `python test_diagnostics.py`

### No OSC in TouchDesigner?
- Port = 7000 in oscin CHOP? ✓
- Active toggle = ON? ✓
- Python app running? ✓
- Click "Reload" in oscin CHOP? ✓

### Tracking Jittery/Shaky?
Edit `config.py`:
```python
SMOOTHING_ALPHA = 0.5  # Instead of 0.7 (smoother)
```

---

## 📚 Documentation Summary

| File | Purpose | Read If... |
|------|---------|-----------|
| **QUICKSTART.md** | 5-min overview | You want to start NOW |
| **README.md** | Complete reference | You need technical details |
| **TOUCHDESIGNER_EXAMPLES.md** | 8 TD examples | You're building in TouchDesigner |
| **PROJECT_OVERVIEW.md** | Architecture guide | You want to understand the code |
| **config.py** | Custom settings | You want to tweak parameters |

---

## 🚀 Your First Project: Hand-Controlled Sphere

### Network in TouchDesigner:
```
oscin (port 7000)
├─ select1 (channel: hand_0_wrist_x)
│  └─ math1 (multiply: 10) → geo1.t.x
│
├─ select2 (channel: hand_0_wrist_y) 
│  └─ math2 (multiply: 10) → geo1.t.y
│
└─ select3 (channel: hand_0_pinch)
   └─ math3 (multiply: 5 add: 0.5) → geo1.s.x (scale)
```

### Result:
- Hand position moves sphere XY
- Pinching scales the sphere
- Open hand = normal size
- Fully pinched = 5× bigger

**That's it!** Now you know how to use gesture data. Check TOUCHDESIGNER_EXAMPLES.md for 7 more ideas.

---

## 💡 Key Concepts

### What Gets Sent to TouchDesigner?

Every frame (~30x per second), 10 values arrive:

```
Hand 0 (Right):
  /hand/0/wrist/x    → float 0.0-1.0 (left-right)
  /hand/0/wrist/y    → float 0.0-1.0 (top-bottom)
  /hand/0/pinch      → float 0.0-1.0 (how pinched)
  /hand/0/openness   → float 0.0-1.0 (how open)
  /hand/0/present    → int 0 or 1 (detected?)

Hand 1 (Left): Same addresses with /hand/1/
```

### How are Gestures Calculated?

**Pinch:** Distance between thumb and index finger
- 0.0 = open (far apart)
- 1.0 = pinched (touching)

**Openness:** Average distance of all fingers from wrist
- 0.0 = closed fist
- 1.0 = fully open hand

**Wrist Position:** Direct X, Y from landmark
- 0.0 = left/top edge
- 1.0 = right/bottom edge

**Hand Present:** Is hand detected?
- 0 = not detected (send zeros)
- 1 = detected (send real values)

---

## ⚙️ Customization (config.py)

Without touching code, change these in `config.py`:

```python
# Where to send
OSC_HOST = 'localhost'    # Change to 192.168.1.5 for other machine
OSC_PORT = 7000           # Different port if needed

# How fast
TARGET_FPS = 30           # More = faster but higher CPU
WEBCAM_WIDTH = 1280       # Lower for better FPS
WEBCAM_HEIGHT = 720

# How smooth
SMOOTHING_ALPHA = 0.7     # 0.5=very smooth, 0.9=very jittery

# How sensitive
PINCH_MAX_DISTANCE = 0.15       # Wider = less sensitive
OPENNESS_MIN_DISTANCE = 0.15    # Lower = easier to trigger
```

Then: `python run.py`

---

## 🆘 Troubleshooting

**Problem** → **Solution**

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named...` | `pip install -r requirements.txt` |
| Webcam black/empty | Check camera permission, try different camera index |
| No hand detected | Better lighting, closer to camera, clean lens |
| OSC not in TD | Port = 7000? Active = ON? Click Reload? |
| Shaky values | Lower SMOOTHING_ALPHA to 0.5 in config |
| Low FPS | Close apps, lower resolution in config |
| Python crashes | Run `python test_diagnostics.py` to debug |

---

## 📖 Full Documentation

Once running, check these for deeper info:

1. **For setup issues:** `setup_check.py` or `test_diagnostics.py`
2. **For technical details:** `README.md`  
3. **For TD integration:** `TOUCHDESIGNER_EXAMPLES.md`
4. **For code details:** Read `hand_tracker.py` (well-commented)
5. **For settings:** Edit `config.py` (all options documented)

---

## ✨ Next Steps

1. **Run:** `python run.py`
2. **See:** Debug window with hands
3. **Connect:** OSC In CHOP in TouchDesigner
4. **Build:** Follow TOUCHDESIGNER_EXAMPLES.md
5. **Create:** Your interactive project!

---

## 🎬 You're All Set!

Everything you need is ready:
- ✅ Hand detection (MediaPipe)
- ✅ Gesture calculation (pinch, openness)
- ✅ OSC transmission (TouchDesigner)
- ✅ Smooth tracking (EMA filtering)
- ✅ Live visualization (debug window)
- ✅ Full documentation
- ✅ Example code
- ✅ Diagnostic tools

**Now:** `python run.py` and start creating! 🚀

---

**Questions?** 
- Check README.md for detailed reference
- Check TOUCHDESIGNER_EXAMPLES.md for integration help
- Run test_diagnostics.py if something doesn't work
- Edit config.py to customize behavior

Happy creating! ✨
