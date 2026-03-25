"""
Diagnostic test script for Hand Tracking Bridge
Tests OSC connectivity and MediaPipe setup independently
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_osc_connectivity(host='localhost', port=7000):
    """Test OSC client connectivity."""
    print("\n" + "=" * 60)
    print("OSC Connectivity Test")
    print("=" * 60)
    
    try:
        from pythonosc import udp_client
        
        client = udp_client.SimpleUDPClient(host, port)
        print(f"✓ Created OSC client for {host}:{port}")
        
        # Send test messages
        test_messages = [
            ("/hand/0/wrist/x", 0.5),
            ("/hand/0/wrist/y", 0.5),
            ("/hand/0/pinch", 0.0),
            ("/hand/0/openness", 1.0),
            ("/hand/0/present", 1),
        ]
        
        print("\nSending test messages:")
        for addr, value in test_messages:
            try:
                client.send_message(addr, value)
                print(f"  ✓ {addr} = {value}")
            except Exception as e:
                print(f"  ❌ {addr} - {e}")
                return False
        
        print("\n✓ OSC connectivity test PASSED")
        print("\nNote: If TouchDesigner isn't receiving messages:")
        print("  - Verify OSC In CHOP port is 7000")
        print("  - Check firewall settings")
        print("  - Verify TouchDesigner is running on same machine")
        return True
        
    except ImportError:
        print("❌ python-osc not installed")
        print("   Install with: pip install python-osc")
        return False
    except Exception as e:
        print(f"❌ OSC test failed: {e}")
        return False


def test_mediapipe():
    """Test MediaPipe Hands setup."""
    print("\n" + "=" * 60)
    print("MediaPipe Hands Test")
    print("=" * 60)
    
    try:
        import mediapipe as mp
        print("✓ mediapipe imported successfully")
        
        # Initialize MediaPipe Hands
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        print("✓ MediaPipe Hands initialized")
        print(f"  - Max hands: 2")
        print(f"  - Detection confidence: 0.7")
        print(f"  - Tracking confidence: 0.5")
        
        print("\n✓ MediaPipe test PASSED")
        return True
        
    except ImportError:
        print("❌ mediapipe not installed")
        print("   Install with: pip install mediapipe")
        return False
    except Exception as e:
        print(f"❌ MediaPipe test failed: {e}")
        return False


def test_opencv():
    """Test OpenCV and webcam access."""
    print("\n" + "=" * 60)
    print("OpenCV and Webcam Test")
    print("=" * 60)
    
    try:
        import cv2
        print(f"✓ OpenCV {cv2.__version__} imported successfully")
        
        # Attempt to open webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Webcam not accessible")
            print("   - Check if another app is using it")
            print("   - Verify camera permissions")
            print("   - Try a different camera index (0, 1, 2, etc.)")
            return False
        
        # Read a frame
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            h, w = frame.shape[:2]
            print(f"✓ Webcam opened successfully")
            print(f"  - Resolution: {w}x{h}")
            print(f"  - Frame shape: {frame.shape}")
            print("\n✓ OpenCV and Webcam test PASSED")
            return True
        else:
            print("❌ Failed to capture frame from webcam")
            return False
            
    except ImportError:
        print("❌ opencv-python not installed")
        print("   Install with: pip install opencv-python")
        return False
    except Exception as e:
        print(f"❌ OpenCV test failed: {e}")
        return False


def test_numpy():
    """Test NumPy."""
    print("\n" + "=" * 60)
    print("NumPy Test")
    print("=" * 60)
    
    try:
        import numpy as np
        print(f"✓ NumPy {np.__version__} imported successfully")
        
        # Simple operation
        arr = np.array([1, 2, 3, 4, 5])
        mean = np.mean(arr)
        print(f"✓ NumPy operations working (mean of [1,2,3,4,5] = {mean})")
        
        print("\n✓ NumPy test PASSED")
        return True
        
    except ImportError:
        print("❌ numpy not installed")
        print("   Install with: pip install numpy")
        return False
    except Exception as e:
        print(f"❌ NumPy test failed: {e}")
        return False


def test_gesture_calculations():
    """Test gesture calculation functions."""
    print("\n" + "=" * 60)
    print("Gesture Calculation Test")
    print("=" * 60)
    
    try:
        import numpy as np
        
        # Mock landmarks (21 points, each with x,y,z)
        landmarks = np.array([
            [0.5, 0.5, 0.0],  # 0: Wrist
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.6, 0.3, 0.0],  # 4: Thumb tip
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.6, 0.2, 0.0],  # 8: Index tip
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.65, 0.1, 0.0], # 12: Middle tip
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.6, 0.0, 0.0],  # 16: Ring tip
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.0, 0.0, 0.0],  # padding
            [0.55, -0.1, 0.0], # 20: Pinky tip
        ])
        
        # Test pinch calculation
        THUMB_TIP = 4
        INDEX_TIP = 8
        thumb = landmarks[THUMB_TIP]
        index = landmarks[INDEX_TIP]
        distance = np.linalg.norm(thumb - index)
        pinch = np.clip(1.0 - (distance / 0.15), 0.0, 1.0)
        
        print(f"✓ Pinch calculation working")
        print(f"  - Thumb: {thumb}")
        print(f"  - Index: {index}")
        print(f"  - Distance: {distance:.4f}")
        print(f"  - Pinch value: {pinch:.4f}")
        
        # Test openness calculation
        WRIST = 0
        FINGERTIPS = [4, 8, 12, 16, 20]
        wrist = landmarks[WRIST]
        fingertip_distances = []
        for tip_idx in FINGERTIPS:
            tip = landmarks[tip_idx]
            d = np.linalg.norm(tip - wrist)
            fingertip_distances.append(d)
        
        avg_distance = np.mean(fingertip_distances)
        openness = np.clip((avg_distance - 0.15) / 0.4, 0.0, 1.0)
        
        print(f"\n✓ Openness calculation working")
        print(f"  - Fingertip distances: {[f'{d:.4f}' for d in fingertip_distances]}")
        print(f"  - Average distance: {avg_distance:.4f}")
        print(f"  - Openness value: {openness:.4f}")
        
        # Test EMA smoothing
        alpha = 0.7
        old_val = 0.5
        new_val = 0.8
        smoothed = alpha * new_val + (1 - alpha) * old_val
        
        print(f"\n✓ EMA smoothing working")
        print(f"  - Old value: {old_val}")
        print(f"  - New value: {new_val}")
        print(f"  - Alpha: {alpha}")
        print(f"  - Smoothed: {smoothed:.4f}")
        
        print("\n✓ Gesture calculation test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Gesture calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    print("\n" + "=" * 70)
    print("Hand Tracking Bridge - Diagnostic Tests")
    print("=" * 70)
    
    tests = [
        ("NumPy", test_numpy),
        ("OpenCV & Webcam", test_opencv),
        ("MediaPipe", test_mediapipe),
        ("Gesture Calculations", test_gesture_calculations),
        ("OSC Connectivity", test_osc_connectivity),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! You're ready to run hand_tracker.py")
        print("  Command: python run.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        print("   Install missing packages with: pip install -r requirements.txt")
    
    print("=" * 70 + "\n")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
