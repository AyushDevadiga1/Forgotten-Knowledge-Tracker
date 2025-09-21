# App entry point for Forgotten Knowledge Tracker
from flask import Flask
import threading
import time
import os
from PIL import Image
# Core modules
from core import tracker, screenshot, ocr, audio, video_attn,intent,knowledge
from config import SCREENSHOT_INTERVAL
from core.ocr import run_ocr 

# -------------------------
# Flask app
# -------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Forgotten Knowledge Tracker is running!"

# -------------------------
# Workers for Phase 2 (OCR) and Phase 3 (Audio)
# -------------------------

def ocr_worker():
    os.makedirs("screenshots", exist_ok=True)
    while True:
        try:
            file_path = screenshot.capture_screenshot()
            text, keywords = ocr.run_ocr(file_path)
            print(f"[OCR] Keywords: {keywords[:10]}")
            # Ensure PIL image closed inside run_ocr
        except Exception as e:
            print("[OCR Error]", e)
        time.sleep(SCREENSHOT_INTERVAL)


def audio_worker():
    while True:
        try:
            audio_clip = audio.record_audio()
            label, conf = audio.classify_audio(audio_clip)
            print(f"[Audio] Detected: {label} ({conf*100:.1f}%)")
        except Exception as e:
            print("[Audio Error]", e)
        time.sleep(5)


def intent_worker():
    while True:
        label, conf = intent.classify_intent()
        if label:
            print(f"[Intent] User is: {label} (confidence: {conf*100:.1f}%)")
        time.sleep(5)  # classify every 5 seconds

def knowledge_worker():
    while True:
        G = knowledge.build_knowledge_graph()
        knowledge.print_graph_summary(G)
        time.sleep(60)  # update every minute



if __name__ == "__main__":
    # Start other background modules (tracking, OCR, audio, webcam, intent)
    t1 = threading.Thread(target=tracker.start_tracking, daemon=True)
    t1.start()
    t2 = threading.Thread(target=ocr_worker, daemon=True)
    t2.start()
    t3 = threading.Thread(target=audio_worker, daemon=True)
    t3.start()
    t4 = threading.Thread(target=video_attn.start_attention_tracking, daemon=True)
    t4.start()
    t5 = threading.Thread(target=intent_worker, daemon=True)
    t5.start()
    
    # Knowledge graph builder
    t6 = threading.Thread(target=knowledge_worker, daemon=True)
    t6.start()
    
    # Run dashboard
    app.run(debug=True, port=5000)