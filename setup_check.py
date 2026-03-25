"""
Installation and setup helper for Hand Tracking Bridge
Validates dependencies and system setup
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.8 or higher."""
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ required, but {sys.version} found")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True


def check_pip():
    """Check if pip is available."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✓ pip is available")
        return True
    except subprocess.CalledProcessError:
        print("❌ pip is not available")
        return False


def install_requirements():
    """Install required packages from requirements.txt."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    print("\nInstalling dependencies from requirements.txt...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )
        print("✓ All dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def verify_imports():
    """Verify that all required packages can be imported."""
    packages = {
        'cv2': 'opencv-python',
        'mediapipe': 'mediapipe',
        'pythonosc': 'python-osc',
        'numpy': 'numpy',
    }
    
    print("\nVerifying imports:")
    all_ok = True
    
    for module, package in packages.items():
        try:
            __import__(module)
            print(f"✓ {module} ({package})")
        except ImportError:
            print(f"❌ {module} ({package}) - NOT INSTALLED")
            all_ok = False
    
    return all_ok


def check_webcam():
    """Check if webcam is accessible."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.release()
            print("\n✓ Webcam is accessible")
            return True
        else:
            print("\n❌ Webcam not accessible (may need permissions)")
            return False
    except Exception as e:
        print(f"\n❌ Error checking webcam: {e}")
        return False


def main():
    """Run all setup checks."""
    print("=" * 60)
    print("Hand Tracking Bridge - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Pip Availability", check_pip),
    ]
    
    print("\nRunning basic checks:")
    for name, check_fn in checks:
        if not check_fn():
            print(f"\n❌ Setup failed: {name} check failed")
            return False
    
    # Ask about installation
    print("\n" + "=" * 60)
    response = input("Install dependencies? (y/n): ").strip().lower()
    if response == 'y':
        if not install_requirements():
            return False
    
    # Verify imports
    if not verify_imports():
        print("\n⚠️  Some packages are not installed. Please run:")
        print(f"   {sys.executable} -m pip install -r requirements.txt")
        return False
    
    # Check webcam
    if not check_webcam():
        print("\n⚠️  Webcam check failed. Ensure:")
        print("   - Webcam is connected")
        print("   - No other app is using it")
        print("   - Application has webcam permissions")
    
    print("\n" + "=" * 60)
    print("✓ Setup verification complete!")
    print("\nTo start hand tracking:")
    print("   python hand_tracker.py")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
