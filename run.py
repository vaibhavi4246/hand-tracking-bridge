"""
Quick start script for Hand Tracking Bridge
Load configuration and start the application
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hand_tracker import HandTracker
from config import (
    OSC_HOST, OSC_PORT, TARGET_FPS, WEBCAM_WIDTH, WEBCAM_HEIGHT,
    SMOOTHING_ALPHA, MIN_DETECTION_CONFIDENCE, MIN_TRACKING_CONFIDENCE
)
import logging


def configure_logging(log_level='INFO', log_file=None):
    """Configure logging."""
    if log_file:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )


def main():
    """Main entry point with configuration."""
    print("=" * 70)
    print("Hand Tracking Bridge for TouchDesigner")
    print("=" * 70)
    
    print("\n📋 Configuration:")
    print(f"   OSC Target: {OSC_HOST}:{OSC_PORT}")
    print(f"   Target FPS: {TARGET_FPS}")
    print(f"   Webcam Resolution: {WEBCAM_WIDTH}x{WEBCAM_HEIGHT}")
    print(f"   Smoothing Alpha: {SMOOTHING_ALPHA}")
    print(f"   Detection Confidence: {MIN_DETECTION_CONFIDENCE}")
    
    print("\n🎥 Starting hand tracking...")
    print("   Press 'q' or close window to quit\n")
    
    try:
        tracker = HandTracker(
            osc_host=OSC_HOST,
            osc_port=OSC_PORT
        )
        
        # Update smoothing from config
        tracker.alpha = SMOOTHING_ALPHA
        
        tracker.run(target_fps=TARGET_FPS)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("👋 Application closed\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
