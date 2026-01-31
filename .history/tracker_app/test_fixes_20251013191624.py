# system_check.py
import sys
import os

def check_system():
    """Check if all system components are working"""
    print("=== SYSTEM STATUS CHECK ===")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check imports
    print("\nChecking imports...")
    try:
        import cv2
        print("✅ OpenCV")
    except ImportError as e:
        print(f"❌ OpenCV: {e}")
    
    try:
        import dlib
        print("✅ dlib")
    except ImportError as e:
        print(f"❌ dlib: {e}")
    
    try:
        import pytesseract
        print("✅ pytesseract")
    except ImportError as e:
        print(f"❌ pytesseract: {e}")
    
    try:
        import sounddevice
        print("✅ sounddevice")
    except ImportError as e:
        print(f"❌ sounddevice: {e}")
    
    try:
        import librosa
        print("✅ librosa")
    except ImportError as e:
        print(f"❌ librosa: {e}")
    
    try:
        import pynput
        print("✅ pynput")
    except ImportError as e:
        print(f"❌ pynput: {e}")
    
    try:
        import win32gui
        print("✅ win32gui")
    except ImportError as e:
        print(f"❌ win32gui: {e}")
    
    # Check model files
    print("\nChecking model files...")
    model_files = [
        "core/intent_classifier.pkl",
        "core/intent_label_map.pkl", 
        "core/audio_classifier.pkl",
        "core/shape_predictor_68_face_landmarks.dat"
    ]
    
    for model_file in model_files:
        if os.path.exists(model_file):
            print(f"✅ {model_file}")
        else:
            print(f"❌ {model_file} - NOT FOUND")
    
    # Check data directory
    print("\nChecking data directory...")
    if os.path.exists("data"):
        print("✅ data directory exists")
    else:
        print("❌ data directory missing")
        os.makedirs("data", exist_ok=True)
        print("Created data directory")
    
    print("\n=== SYSTEM CHECK COMPLETE ===")

if __name__ == "__main__":
    check_system()