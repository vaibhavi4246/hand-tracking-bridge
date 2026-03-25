"""Quick camera test script"""
import cv2

print("Testing webcam access...")

# Try different camera indices
for i in range(5):
    print(f"\nTrying camera {i}...")
    cap = cv2.VideoCapture(i)
    
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"✓ SUCCESS! Camera {i} works - Resolution: {w}x{h}")
            cap.release()
            print(f"\nUpdate config.py or hand_tracker.py to use camera index {i}")
            break
        else:
            print(f"✗ Camera {i} opened but can't read frames")
            cap.release()
    else:
        print(f"✗ Camera {i} not available")

print("\nDone!")
