# core/preflight_check.py
import os
import pickle
import numpy as np
from core.db_module import init_db, init_multi_modal_db
from core.audio_module import record_audio, extract_features as audio_extract_features, classify_audio
from core.intent_module import extract_features as intent_extract_features, predict_intent
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
from core.face_detection_module import FaceDetector
from core.knowledge_graph import get_graph

# -----------------------------
# Classifier & Label Check
# -----------------------------
def check_classifiers():
    print("Checking classifiers...")
    audio_clf_loaded = False
    intent_clf_loaded = False

    if os.path.exists("core/audio_classifier.pkl"):
        with open("core/audio_classifier.pkl", "rb") as f:
            audio_clf = pickle.load(f)
        audio_clf_loaded = True
    if os.path.exists("core/intent_classifier.pkl") and os.path.exists("core/intent_label_map.pkl"):
        with open("core/intent_classifier.pkl", "rb") as f:
            intent_clf = pickle.load(f)
        with open("core/intent_label_map.pkl", "rb") as f:
            intent_label_map = pickle.load(f)
        intent_clf_loaded = True

    print("Audio classifier loaded:", audio_clf_loaded)
    print("Intent classifier & label map loaded:", intent_clf_loaded)

# -----------------------------
# Database Check
# -----------------------------
def check_database():
    print("Checking database tables...")
    init_db()
    init_multi_modal_db()
    print("Database initialized successfully.")

# -----------------------------
# Feature Extraction Check
# -----------------------------
def check_features():
    print("Checking feature extraction...")

    # Audio
    dummy_audio = np.zeros(16000)
    audio_feat = audio_extract_features(dummy_audio)
    print("Audio features shape:", audio_feat.shape)

    # Intent
    intent_feat = intent_extract_features({}, "silence", 0, 0)
    print("Intent features shape:", intent_feat.shape)

# -----------------------------
# Multi-Modal Pipelines
# -----------------------------
def check_pipelines():
    print("Checking OCR pipeline...")
    ocr_result = ocr_pipeline()
    print("OCR pipeline output:", ocr_result)

    print("Checking audio classification...")
    label, conf = classify_audio(np.zeros(16000))
    print("Audio classification output:", label, conf)

    print("Checking webcam pipeline (if available)...")
    try:
        frame = webcam_pipeline()
        faces, num_faces = FaceDetector().detect_faces(frame)
        print("Webcam detected faces:", num_faces)
    except Exception as e:
        print("Webcam pipeline skipped/error:", e)

# -----------------------------
# Knowledge Graph
# -----------------------------
def check_knowledge_graph():
    print("Checking knowledge graph load/save...")
    G = get_graph()
    try:
        import pickle
        with open("data/knowledge_graph_test.pkl", "wb") as f:
            pickle.dump(G, f)
        print("Knowledge graph save test passed.")
    except Exception as e:
        print("Knowledge graph save failed:", e)

# -----------------------------
# Dry run logging
# -----------------------------
def dry_run_logging():
    print("Performing dry run of session logging...")
    from core.tracker import get_active_window, log_session
    for _ in range(2):
        window, interaction = get_active_window()
        log_session(window, interaction)
        print(f"Logged session for window: {window} | Interaction: {interaction}")

# -----------------------------
# Run all checks
# -----------------------------
if __name__ == "__main__":
    print("=== PRE-FLIGHT CHECK START ===")
    check_classifiers()
    check_database()
    check_features()
    check_pipelines()
    check_knowledge_graph()
    dry_run_logging()
    print("=== PRE-FLIGHT CHECK COMPLETED ===")
