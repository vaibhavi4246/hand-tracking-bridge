# TouchDesigner Integration Guide

Complete examples for using hand tracking OSC data in TouchDesigner.

## Setup Checklist

- [ ] Python app running (`python run.py`)
- [ ] OSC In CHOP created and port set to 7000
- [ ] "Active" toggle turned ON in OSC In CHOP
- [ ] Channels appearing in OSC In CHOP (check "Reload")

## Example 1: Hand Position Tracking

**Goal:** Make geometry follow hand position in 3D space

### Network Setup

```
oscin (port 7000, active ON)
  ├─ select (channel: hand_0_wrist_x) → math → text (display X)
  ├─ select (channel: hand_0_wrist_y) → math → text (display Y)
  └─ to: geo1 translate X (X value)
       to: geo1 translate Y (Y value)
```

### Details

**Select CHOP for X position:**
- Channel pattern: `hand_0_wrist_x`
- Output: 0.0-1.0

**Math CHOP for scaling:**
```
Input: select output
Multiply: 10 (for 10 units of movement)
Output: 0-10
```

**Connect to Geometry:**
- Drag select output → geo1.t.x (translate X)
- Drag select output → geo1.t.y (translate Y, inverted)

---

## Example 2: Pinch to Scale

**Goal:** Scale geometry based on pinch intensity

### Network Setup

```
oscin (port 7000)
  └─ select (hand_0_pinch) 
       └─ math (remap 0-1 → 0.5-2.0)
            └─ to: geo1.scale.xyz
```

### Details

**Math CHOP settings:**
```
Pre:  *1.5      (scale amplification)
Add:  +0.5      (offset for minimum scale)
```

Result: Pinch value 0.0 = scale 0.5x, Pinch = 1.0 = scale 2.0x

---

## Example 3: Hand Openness to Rotation

**Goal:** Rotate geometry based on hand openness

### Network Setup

```
oscin (port 7000)
  └─ select (hand_0_openness)
       └─ math (multiply by 360)
            └─ to: geo1.r.z (rotate Z)
```

### Details

Maps openness (0.0-1.0) to rotation (0-360 degrees)
- Closed fist = 0 degrees
- Open hand = 360 degrees

---

## Example 4: Two-Hand Control

**Goal:** Use both hands for complex control

### Network Setup

```
oscin (port 7000)
  ├─ right hand:
  │   ├─ select (hand_0_wrist_x) → geo1.t.x
  │   ├─ select (hand_0_wrist_y) → geo1.t.y
  │   └─ select (hand_0_pinch) → geo1.s.x
  │
  └─ left hand:
       ├─ select (hand_1_wrist_x) → geo2.t.x
       ├─ select (hand_1_wrist_y) → geo2.t.y
       └─ select (hand_1_openness) → geo2.s.y
```

**Logic:**
- Right hand position controls first geometric position
- Right hand pinch controls first geo X-scale
- Left hand position controls second geo position
- Left hand openness controls second geo Y-scale

---

## Example 5: Hand Presence Detection

**Goal:** Show/hide geometry based on hand detection

### Network Setup

```
oscin (port 7000)
  └─ select (hand_0_present)
       └─ logic (convert to boolean)
            └─ to: geo1.display (show/hide)
```

### Details

**Logic CHOP:**
- Input: hand_0_present (0 or 1)
- Output: 1 if input > 0.5, else 0

**Connect to display:**
- Drag logic output → right-click geo1 → "Set ... in Operator"

Alternatively, use in Null CHOP with viewer:
```
select (hand_0_present) 
  → logic (>0.5)
     → null (to monitor boolean)
```

Then reference in geo display callback or Python script.

---

## Example 6: Gesture-Based Animation Trigger

**Goal:** Trigger animations when hand performs gesture

### Python Script Approach

**Create Text DAT with script:**

```python
def onCook(scriptOp):
    # Get current hand values
    pinch = op('oscin')['hand_0_pinch'][0].val
    openness = op('oscin')['hand_0_openness'][0].val
    present = op('oscin')['hand_0_present'][0].val
    
    if present == 0:
        scriptOp.text = "No hand detected"
        return
    
    # Trigger animation on strong pinch
    if pinch > 0.8:
        op('geo1').play = True  # Start animation
        scriptOp.text = "Pinch detected! Playing animation"
    else:
        scriptOp.text = f"Pinch: {pinch:.2f}, Open: {openness:.2f}"
```

**Network:**
```
oscin → text_dat (with above script) 
     → display in status area
```

---

## Example 7: Multi-Parameter Mapping

**Goal:** Map all gesture data to audio/visual synthesis

### Complete Network

```
oscin (port 7000)
  ├─ hand 0 (right):
  │   ├─ wrist_x → osc_wave (frequency modulation)
  │   ├─ wrist_y → audio_lib (volume)
  │   ├─ pinch → audio_lib (filter cutoff)
  │   └─ openness → par.hue_shift
  │
  └─ hand 1 (left):
       ├─ pinch → par.saturation
       ├─ openness → par.brightness
       └─ present → par.enable_effect
```

### Details

**Hand 0 → Audio:**
```
select (hand_0_wrist_x) 
  → math (*440) → osc1.freq  (20-20kHz range)

select (hand_0_wrist_y)
  → math (*1.0) → audio_lib.volume  (0-1 range)

select (hand_0_pinch)
  → math (*20000) → audio_lib.filter_cutoff  (0-20000Hz)
```

**Hand 0 → Visual:**
```
select (hand_0_openness)
  → math (*360) → par.hue_shift

select (hand_0_pinch)
  → math (*100) → par.saturation  (%)
```

**Hand 1 → Effects:**
```
select (hand_1_openness)
  → math (*100) → par.brightness  (%)

select (hand_1_present)
  → logic (>0.5) → par.enable_effect
```

---

## Example 8: Debug Monitor

**Goal:** Display all OSC values in real-time

### Panel Setup

```
Container COMP
├─ Text COMP (FPS)
├─ Text COMP (Hand 0 Status)
├─ Text COMP (Hand 1 Status)
├─ Text COMP (Gesture Values)
└─ Null CHOP (monitor output)
```

### Python DAT Script

```python
def onCook(scriptOp):
    # Read OSC input
    osc_in = op('oscin')
    
    lines = [
        "=== HAND TRACKING DEBUG ===",
        "",
        "HAND 0 (Right):",
    ]
    
    try:
        present_0 = osc_in['hand_0_present'][0].val
        if present_0 > 0:
            wx = osc_in['hand_0_wrist_x'][0].val
            wy = osc_in['hand_0_wrist_y'][0].val
            pinch = osc_in['hand_0_pinch'][0].val
            openness = osc_in['hand_0_openness'][0].val
            
            lines.append(f"  Wrist: ({wx:.3f}, {wy:.3f})")
            lines.append(f"  Pinch: {pinch:.3f}")
            lines.append(f"  Openness: {openness:.3f}")
        else:
            lines.append("  [NOT DETECTED]")
    except:
        lines.append("  [ERROR]")
    
    lines.append("")
    lines.append("HAND 1 (Left):")
    
    try:
        present_1 = osc_in['hand_1_present'][0].val
        if present_1 > 0:
            wx = osc_in['hand_1_wrist_x'][0].val
            wy = osc_in['hand_1_wrist_y'][0].val
            pinch = osc_in['hand_1_pinch'][0].val
            openness = osc_in['hand_1_openness'][0].val
            
            lines.append(f"  Wrist: ({wx:.3f}, {wy:.3f})")
            lines.append(f"  Pinch: {pinch:.3f}")
            lines.append(f"  Openness: {openness:.3f}")
        else:
            lines.append("  [NOT DETECTED]")
    except:
        lines.append("  [ERROR]")
    
    scriptOp.text = "\n".join(lines)
```

---

## Tips & Tricks

### 1. Deadzone Filter
Prevent tiny movements from affecting parameters:

```
select (hand_0_wrist_x)
  → chop (add logic for deadzone)
    → out: clamp(x, 0.1, 0.9)
```

### 2. Gesture Combinations
Trigger action when both hands pinch simultaneously:

```
select (hand_0_pinch) AND select (hand_1_pinch)
  → logic (AND if both > 0.8)
    → trigger_action
```

### 3. Smoothing in TouchDesigner
Add extra smoothing in addition to Python app:

```
select (hand_0_wrist_x)
  → lfo (use as smooth node, frequency:0.5Hz)
    → out: smoothed position
```

### 4. Recording Gestures
Capture hand data for playback/review:

```
oscin → record (DAT recording mode)
```

Save recordings for gesture detection training or playback.

---

## Performance Notes

- OSC updates at 30 FPS from Python app
- TouchDesigner will receive 30 channels per frame
- No additional filtering needed in most cases
- Use Monitor CHOPs to visualize data flow
- Disable visualization if hitting performance limits

---

## Troubleshooting in TouchDesigner

**Channels not appearing:**
- Check OSC In CHOP "Active" is ON
- Click "Reload" button
- Check Python app is running (window title shows hand tracking)
- Verify port 7000 in Python matches OSC In CHOP

**Values stuck at 0:**
- Check "hand_N_present" is 1 (not 0)
- Move hand in front of camera
- Check lighting

**Delayed response:**
- Check FPS (target 30 with Python app)
- Reduce number of CHOP operations
- Profile with Monitor CHOPs

**Unexpected values:**
- Check normalization (0-1 for position, 0-1 for gestures)
- Verify Math CHOPs aren't double-processing
- Monitor raw OSC input with null CHOP

---

## Next: Build Your Project!

Use these examples as building blocks for your interactive installation, performance tool, or realtime visualization.

Have fun! 🎬✨
