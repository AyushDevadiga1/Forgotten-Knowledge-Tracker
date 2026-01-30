# install_dependencies.py
import subprocess
import sys

def install(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"[OK] {package} installed successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to install {package}: {e}")
        return False

def main():
    print("[SETUP] Installing dependencies...")
    packages = [
        "numpy", "pandas", "scikit-learn", "xgboost",
        "librosa", "sounddevice", "pynput", "pywin32",
        "opencv-python", "pytesseract", "mss",
        "keybert", "sentence-transformers", "spacy",
        "networkx", "plotly", "streamlit", "plyer",
        "dlib", "imutils"
    ]

    installed = 0
    for pkg in packages:
        if install(pkg):
            installed += 1

    # Download spaCy model
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("[OK] spaCy model downloaded successfully")
    except Exception as e:
        print(f"[FAIL] Failed to download spaCy model: {e}")

    print(f"\n[RESULT] Installed {installed}/{len(packages)} packages successfully")

if __name__ == "__main__":
    main()
