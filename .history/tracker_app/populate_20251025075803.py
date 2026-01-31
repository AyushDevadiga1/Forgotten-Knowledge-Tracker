import sqlite3
import random
from datetime import datetime, timedelta
import itertools


# -----------------------------
# Edge-case scenarios for reference
# -----------------------------
eye_tracking = [
    "Eyes open and focused", "Eyes open but slightly distracted", "Normal blinking",
    "Small head movements", "Looking at intended target", "Eyes closed",
    "Extended eye closure", "Eyes partially covered", "Glasses glare",
    "Face partially out of frame", "Rapid or erratic eye movement", "Head turned away",
    "Low/bright lighting", "Camera malfunction", "False positives/negatives",
    "Intentional gaze shift", "Multitasking/divided attention", "Microexpressions",
    "Occlusion + poor lighting", "Abnormal blinking patterns", "Sudden head jerk",
    "Temporary occlusion"
]

audio_scenarios = [
    "Clear speech detected", "Soft background speech", "Speaking relevant content",
    "Normal tone and pace", "Intermittent silence", "No audio detected",
    "Extremely low volume", "Extremely high volume or shouting", "Muffled/distorted audio",
    "Overlapping speech", "Long silence", "Background noise too high",
    "Echo or feedback", "Microphone malfunction", "Speech not relevant to task",
    "Rapid speech or stammering", "Pauses mid-sentence", "Intentional whispers",
    "Background conversation partially audible", "Audio delayed or lagging",
    "Mixed emotions in tone", "Environmental disruptions"
]

ocr_scenarios = [
    "Keywords detected correctly", "Partial keywords detected", "High confidence OCR",
    "Dynamic content captured properly", "Multiple keywords in sequence",
    "No text detected", "Mislabeled/incorrect text detected", "Low-quality/blurry screen",
    "Obstructed screen", "Small font", "Screen glare/reflections", "Unusual font/color",
    "Dynamic content missed", "Partial screenshot", "Incorrect language/special chars",
    "Multiple windows overlapping", "Text partially occluded", "Fast-changing content",
    "Multiple languages/symbols", "Low contrast text", "Animated text/video overlays",
    "Mixed content (images + text)"
]

keyboard_mouse = [
    "Regular typing activity", "Frequent mouse clicks", "Mouse movement tracking",
    "Short pauses between keystrokes/clicks", "Combination typing + mouse activity",
    "No keyboard activity for long periods", "No mouse movement", "Random/irrelevant keystrokes",
    "Rapid repetitive keystrokes", "Keyboard/mouse malfunction", "Accidental touches/clicks",
    "Mouse moving off-screen repeatedly", "Typing in unrelated app", "Short bursts + idle",
    "Keyboard shortcuts", "Gesture-based input", "Copy-paste activity",
    "Multiple windows open", "External devices", "Keyboard/mouse automation",
    "Slow typing but focused reading", "Idle mouse with active keyboard"
]

# -----------------------------
# Topics / Files (~100 topics)
# -----------------------------
files = [
    # Added all the files you listed + generic topics to reach 100+
    "intent_training_data_edge.csv", "intent_training_data_large.csv", "main.py",
    "merged_logs.csv", "multi_modal_logs_export.csv", "multi_modal_logs_invalid_rows.csv",
    "populate.py", "preflight_check.py", "sessions_export.csv", "sessions_invalid_rows.csv",
    "test_all.py", "test_audio.py", "test_dashboard.py", "test_db.py",
    "test_memory_graph.py", "tracker.db", "train_all_models.py", "train_models_from_logs.py",
    ".pytest_cache", "__pycache__", "core", "dashboard", "data", "htmlcov", "logs",
    "models", "results", "test_data", "tests", "training_data", ".coverage",
    "config.py", "install_dependencies.py", "clean.py", "config.json",
    "data_fetcher.py", "db.py", "debug_all_services.py", "debug_full_system.py",
    "demo.py", "demo_train_and_predict.py", "dummy_data.db", "export_all_data.py",
    "exported_data.json", "FKT 2.pptx", "flowRest.txt", "flowSessions.txt",
    "forgotten_knowledge.db", "generate_test_data.py", "insurance.csv", "migrate_audio_logs.py",
    "pokemon.csv", "preflight_check.py", "review_manager.py", "sample.wav",
    "seed_sessions.py", "session_classifier.joblib", "setup.py", "setup_sessions.py",
    "simulate_sessions.py", "test_endpoints.py", "test_review.py", "test_train.py",
    "tracker.py", "tracking.db", "train_classifier.py", "validate_exported_data.py",
    ".history", "__pycache__", "csv_export", "services", "static", "templates", "venv",
    "activity.db", "activity_log.db", "all.json", "analytics.py", "app.py", "classifier.py",
    "classifier_config.json", "classifier_model.pkl",
    # Dump files
    "1 (19).png","1 (20).png","1 (21).png","1.certificatepg.docx","2.docx","3.docx","AI.pdf",
    "algo.PNG","Angle lines design.pptx","Appflow.txt","Architecture.PNG","audio.PNG",
    "BCE PPT.pptx","BCE.pdf","BCE1.pptx","BCEprax.pptx","Book1.twb","Capture.PNG",
    "Capture1.PNG","Capture2.PNG","Capturedesc.PNG","Capturesteps.PNG",
    "Copilot_20251007_171501.png","Copilot_20251007_171754.png","DA_2026_Syllabus.pdf",
    "daikibo-telemetry-data.json","data.PNG","dc.PNG","deepsite.avif","deepsite-tic-toe-demo.webp",
    "def.txt","Delinquency_prediction_dataset (1).xlsx","Delinquency_prediction_dataset.pdf",
    "Delinquency_prediction_dataset.xlsx","EDA_Example_Answer.docx","EDA_SummaryReport.pdf",
    "EDA_SummaryReport_Template.docx","example_answer_pptx.pptx",
    "Example_Business_Summary_Report.docx","gentelella.webp","Imputation_Guide_Handout.docx",
    "Introduction_merged.pdf","mine.PNG","newBCE.pptx","ocr.PNG","Op1.PNG","Op2.PNG",
    "Pdfiot.docx","Pdfiot.pdf","Pdfiot1.pdf","Presentation_Template.pptx",
    "progress and path.txt","Project Report format.pdf","QB.txt","retention.PNG",
    "scikit-learn-docs.pdf","SQLDocumentation.pdf","Synopsis_with_changes.pdf",
    "Task 2_ModelPlan.pdf","Task 2_ModelPlan_Template.docx","Task 5 Equality Table.xlsx",
    "Task_2_Model_Plan_Example_Answer.docx","Task4.pptx","Tata_Data_Analytics_Glossary (1).docx",
    "tetris.PNG","Timepass.png","Transcript.txt","Updated_Business_Summary_Report.pdf",
    "Updated_Business_Summary_Report_Template.docx","WC 1 to 10 Experiment (1).pdf",
    "WC ASSIGNMENT 2.pdf","wc ex 9.pdf","Word-Letter-A4","1 (1).jpg","1 (1).png","1 (2).jpg",
    "1 (3).jpg","1 (8).png","1 (9).png","1 (10).png","1 (11).png","1 (12).png","1 (13).png",
    "1 (14).png","1 (15).png","1 (16).png","1 (17).png","1 (18).png"
]

# Cycle through topics endlessly
topics_cycle = itertools.cycle(files)

# -----------------------------
# Connect DB
# -----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# Populate sessions (150, avg 10min)
# -----------------------------
print("Populating sessions table...")
for _ in range(150):
    start = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0,23))
    duration_min = random.randint(5,15)
    end = start + timedelta(minutes=duration_min)
    
    cursor.execute("""
        INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        start,
        end,
        random.choice(["VS Code", "PowerPoint", "Chrome", "Excel", "Word", "PyCharm"]),
        next(topics_cycle),
        round(random.uniform(0, 1), 2),
        random.randint(1, 20),
        random.choice(audio_scenarios),
        random.choice(eye_tracking),
        round(random.uniform(0.5,1),2)
    ))

# -----------------------------
# Populate multi-modal logs
# -----------------------------
print("Populating multi-modal logs table...")
for _ in range(200):
    ts = datetime.now() - timedelta(days=random.randint(0,30), hours=random.randint(0,23))
    cursor.execute("""
        INSERT INTO multi_modal_logs (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts,
        next(topics_cycle),
        random.choice(ocr_scenarios),
        random.choice(audio_scenarios),
        round(random.uniform(0,1),2),
        round(random.uniform(0,1),2),
        random.choice(keyboard_mouse),
        round(random.uniform(0.5,1),2),
        round(random.uniform(0,1),2)
    ))

# -----------------------------
# Populate memory decay
# -----------------------------
print("Populating memory_decay table...")
for _ in range(100):
    last_seen = datetime.now() - timedelta(days=random.randint(0,30))
    updated_at = last_seen + timedelta(hours=random.randint(1,72))
    cursor.execute("""
        INSERT INTO memory_decay (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        next(topics_cycle),
        last_seen,
        round(random.uniform(0,1),2),
        random.randint(1,10),
        updated_at
    ))

# -----------------------------
# Populate metrics
# -----------------------------
print("Populating metrics table...")
for _ in range(100):
    next_review = datetime.now() + timedelta(days=random.randint(1,30))
    cursor.execute("""
        INSERT INTO metrics (concept, next_review_time, memory_score)
        VALUES (?, ?, ?)
    """, (
        next(topics_cycle),
        next_review,
        round(random.uniform(0,1),2),
        datetime.now()
    ))

# -----------------------------
# Commit & close
# -----------------------------
conn.commit()
conn.close()
print("Database populated successfully!")
