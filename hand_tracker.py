"""
Hand Tracking Bridge for TouchDesigner via OSC
Tracks hand landmarks using MediaPipe and sends real-time gesture data to TouchDesigner.
"""

import cv2
import mediapipe as mp
import numpy as np
from pythonosc import udp_client
from collections import deque
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HandTracker:
    """
    Real-time hand tracking with OSC output for TouchDesigner.
    
    Detects hand landmarks, calculates gestures, and sends normalized
    values via OSC protocol.
    """
    
    # Landmark indices
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20
    
    # All fingertips for openness calculation
    FINGERTIPS = [THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
    
    def __init__(self, osc_host='localhost', osc_port=7000):
        """
        Initialize MediaPipe and OSC client.
        
        Args:
            osc_host (str): OSC server host
            osc_port (int): OSC server port
        """
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Initialize OSC client
        try:
            self.osc_client = udp_client.SimpleUDPClient(osc_host, osc_port)
            logger.info(f"OSC client initialized: {osc_host}:{osc_port}")
        except Exception as e:
            logger.error(f"Failed to initialize OSC client: {e}")
            self.osc_client = None
        
        # EMA smoothing buffer (alpha=0.7)
        self.smooth_values = {}
        self.alpha = 0.7
        
        # Performance tracking
        self.frame_times = deque(maxlen=30)
        
    def process_frame(self, frame):
        """
        Process a frame and detect hand landmarks.
        
        Args:
            frame (np.ndarray): Input frame from webcam
            
        Returns:
            tuple: (annotated_frame, list of gesture dicts for each hand)
        """
        # Flip frame horizontally for natural interaction
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.hands.process(rgb_frame)
        
        # List to store gesture data for each hand
        gestures_list = []
        
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                # Extract landmarks
                landmarks = np.array([
                    [lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark
                ])
                
                # Calculate gestures
                gesture_dict = {
                    'present': 1,
                    'wrist_x': landmarks[self.WRIST, 0],
                    'wrist_y': 1.0 - landmarks[self.WRIST, 1],  # Invert Y for top=1
                    'pinch': self.calculate_pinch(landmarks),
                    'openness': self.calculate_openness(landmarks),
                }
                
                # Apply smoothing
                for key in ['wrist_x', 'wrist_y', 'pinch', 'openness']:
                    gesture_dict[key] = self.smooth_value(
                        f'hand_{hand_idx}_{key}',
                        gesture_dict[key]
                    )
                
                gestures_list.append(gesture_dict)
                
                # Draw landmarks and connections
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
        
        # Add missing hands with zeroed values
        while len(gestures_list) < 2:
            gestures_list.append({
                'present': 0,
                'wrist_x': 0.0,
                'wrist_y': 0.0,
                'pinch': 0.0,
                'openness': 0.0,
            })
        
        return frame, gestures_list
    
    def calculate_pinch(self, landmarks):
        """
        Calculate pinch gesture as distance between thumb and index finger.
        
        Args:
            landmarks (np.ndarray): Hand landmarks (21, 3)
            
        Returns:
            float: Normalized pinch distance (0.0 to 1.0)
        """
        thumb = landmarks[self.THUMB_TIP]
        index = landmarks[self.INDEX_TIP]
        
        # Euclidean distance
        distance = np.linalg.norm(thumb - index)
        
        # Normalize to 0-1 range (calibrated for typical hand size)
        # Max pinch distance is roughly 0.15 in normalized coords
        pinch = np.clip(1.0 - (distance / 0.15), 0.0, 1.0)
        
        return float(pinch)
    
    def calculate_openness(self, landmarks):
        """
        Calculate hand openness as average distance of fingertips from wrist.
        
        Args:
            landmarks (np.ndarray): Hand landmarks (21, 3)
            
        Returns:
            float: Normalized openness (0.0 to 1.0)
        """
        wrist = landmarks[self.WRIST]
        fingertip_distances = []
        
        for tip_idx in self.FINGERTIPS:
            tip = landmarks[tip_idx]
            distance = np.linalg.norm(tip - wrist)
            fingertip_distances.append(distance)
        
        # Average distance
        avg_distance = np.mean(fingertip_distances)
        
        # Normalize (typical range: 0.2 to 0.5)
        openness = np.clip((avg_distance - 0.15) / 0.4, 0.0, 1.0)
        
        return float(openness)
    
    def smooth_value(self, key, new_val):
        """
        Apply exponential moving average (EMA) smoothing.
        
        Args:
            key (str): Unique key for this value stream
            new_val (float): New value to smooth
            
        Returns:
            float: Smoothed value
        """
        if key not in self.smooth_values:
            self.smooth_values[key] = new_val
            return new_val
        
        old_val = self.smooth_values[key]
        smoothed = self.alpha * new_val + (1 - self.alpha) * old_val
        self.smooth_values[key] = smoothed
        
        return smoothed
    
    def send_osc(self, hand_index, gesture_dict):
        """
        Send OSC messages to TouchDesigner.
        
        Args:
            hand_index (int): Hand index (0 or 1)
            gesture_dict (dict): Gesture data dictionary
        """
        if self.osc_client is None:
            return
        
        try:
            base_addr = f"/hand/{hand_index}"
            
            self.osc_client.send_message(
                f"{base_addr}/wrist/x",
                gesture_dict['wrist_x']
            )
            self.osc_client.send_message(
                f"{base_addr}/wrist/y",
                gesture_dict['wrist_y']
            )
            self.osc_client.send_message(
                f"{base_addr}/pinch",
                gesture_dict['pinch']
            )
            self.osc_client.send_message(
                f"{base_addr}/openness",
                gesture_dict['openness']
            )
            self.osc_client.send_message(
                f"{base_addr}/present",
                gesture_dict['present']
            )
            
            # Debug: Print on every 10th frame
            if not hasattr(self, 'debug_counter'):
                self.debug_counter = 0
            self.debug_counter += 1
            if self.debug_counter % 10 == 0:
                print(f"✓ OSC sent Hand {hand_index}: x={gesture_dict['wrist_x']:.2f} y={gesture_dict['wrist_y']:.2f} pinch={gesture_dict['pinch']:.2f} open={gesture_dict['openness']:.2f}")
                
        except Exception as e:
            logger.error(f"Failed to send OSC message for hand {hand_index}: {e}")
            print(f"❌ OSC ERROR: {e}")
    
    def run(self, target_fps=30):
        """
        Main loop with webcam capture and display.
        
        Args:
            target_fps (int): Target frames per second
        """
        # Open webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            logger.error("Failed to open webcam")
            return
        
        # Set webcam properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, target_fps)
        
        frame_interval = 1.0 / target_fps
        last_time = time.time()
        
        logger.info("Starting hand tracking. Press 'q' to quit.")
        
        try:
            while True:
                current_time = time.time()
                
                # Frame rate control
                if current_time - last_time < frame_interval:
                    time.sleep(0.001)
                    continue
                
                last_time = current_time
                
                # Capture frame
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read frame from webcam")
                    break
                
                # Process frame
                annotated_frame, gestures_list = self.process_frame(frame)
                
                # Send OSC for each hand
                for hand_idx, gesture_dict in enumerate(gestures_list):
                    self.send_osc(hand_idx, gesture_dict)
                
                # Calculate FPS
                self.frame_times.append(1.0 / (time.time() - current_time + 1e-6))
                fps = np.mean(self.frame_times)
                
                # Draw debug information
                annotated_frame = self._draw_debug_info(
                    annotated_frame,
                    gestures_list,
                    fps
                )
                
                # Display frame
                cv2.imshow('Hand Tracking - OSC Bridge', annotated_frame)
                
                # Check for quit key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Quitting...")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            cap.release()
            cv2.destroyAllWindows()
            logger.info("Application closed")
    
    def _draw_debug_info(self, frame, gestures_list, fps):
        """
        Draw debug information on frame.
        
        Args:
            frame (np.ndarray): Frame to draw on
            gestures_list (list): List of gesture dictionaries
            fps (float): Current FPS
            
        Returns:
            np.ndarray: Annotated frame
        """
        h, w = frame.shape[:2]
        
        # Draw FPS counter
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )
        
        # Draw gesture info for each hand
        y_offset = 70
        for hand_idx, gesture in enumerate(gestures_list):
            if gesture['present'] == 0:
                cv2.putText(
                    frame,
                    f"Hand {hand_idx}: Not detected",
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )
            else:
                text = (
                    f"Hand {hand_idx}: "
                    f"Pinch={gesture['pinch']:.2f} "
                    f"Open={gesture['openness']:.2f} "
                    f"Wrist=({gesture['wrist_x']:.2f}, {gesture['wrist_y']:.2f})"
                )
                cv2.putText(
                    frame,
                    text,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
            
            y_offset += 35
        
        return frame


def main():
    """
    Entry point for the application.
    
    TouchDesigner Setup Instructions:
    1. In TouchDesigner, add an OSC In CHOP
    2. Set network port to 7000
    3. The CHOP will auto-create channels matching OSC addresses:
       - /hand/0/wrist/x
       - /hand/0/wrist/y
       - /hand/0/pinch
       - /hand/0/openness
       - /hand/0/present
       - /hand/1/wrist/x
       - /hand/1/wrist/y
       - /hand/1/pinch
       - /hand/1/openness
       - /hand/1/present
    4. Use Select CHOP to isolate individual channels
    5. Map channels to visual parameters using Math CHOP for range remapping
    """
    tracker = HandTracker(osc_host='localhost', osc_port=7000)
    tracker.run(target_fps=30)


if __name__ == '__main__':
    main()
