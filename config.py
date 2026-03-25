"""
Configuration file for Hand Tracking Bridge
Customize parameters without modifying hand_tracker.py
"""

# OSC Configuration
OSC_HOST = 'localhost'
OSC_PORT = 7000

# MediaPipe Configuration
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5
MAX_NUM_HANDS = 2

# Performance Configuration
TARGET_FPS = 30
WEBCAM_WIDTH = 1280
WEBCAM_HEIGHT = 720

# Smoothing Configuration (Exponential Moving Average)
SMOOTHING_ALPHA = 0.7  # Range: 0.0-1.0
                        # 0.0 = maximum smoothing (laggy)
                        # 0.5 = balanced
                        # 1.0 = no smoothing (jittery)

# Gesture Calculation Calibration
PINCH_MAX_DISTANCE = 0.15        # Maximum pinch distance before clamping
OPENNESS_MIN_DISTANCE = 0.15     # Minimum distance for closed fist
OPENNESS_MAX_DISTANCE = 0.55     # Maximum distance for open hand

# Debug Visualization
SHOW_DEBUG_WINDOW = True
DEBUG_TEXT_SCALE = 0.7
DEBUG_TEXT_THICKNESS = 2
FPS_UPDATE_INTERVAL = 30  # Recalculate FPS every N frames

# Logging Configuration
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = None     # Set to filename to log to file, None for console only

# TouchDesigner Integration Notes
# ============================================
# The OSC addresses sent are:
#   /hand/{hand_id}/{param}
#
# Where:
#   hand_id: 0 or 1 (right and left hands)
#   param: wrist/x, wrist/y, pinch, openness, present
#
# All values are normalized 0.0-1.0 (except 'present' which is 0 or 1 int)


def get_config():
    """Return configuration as dictionary."""
    return {
        'osc_host': OSC_HOST,
        'osc_port': OSC_PORT,
        'min_detection_confidence': MIN_DETECTION_CONFIDENCE,
        'min_tracking_confidence': MIN_TRACKING_CONFIDENCE,
        'max_num_hands': MAX_NUM_HANDS,
        'target_fps': TARGET_FPS,
        'webcam_width': WEBCAM_WIDTH,
        'webcam_height': WEBCAM_HEIGHT,
        'smoothing_alpha': SMOOTHING_ALPHA,
        'pinch_max_distance': PINCH_MAX_DISTANCE,
        'openness_min_distance': OPENNESS_MIN_DISTANCE,
        'openness_max_distance': OPENNESS_MAX_DISTANCE,
        'show_debug_window': SHOW_DEBUG_WINDOW,
        'debug_text_scale': DEBUG_TEXT_SCALE,
        'debug_text_thickness': DEBUG_TEXT_THICKNESS,
        'fps_update_interval': FPS_UPDATE_INTERVAL,
        'log_level': LOG_LEVEL,
        'log_file': LOG_FILE,
    }


if __name__ == '__main__':
    # Print current configuration
    import json
    config = get_config()
    print("Current Configuration:")
    print(json.dumps(config, indent=2))
