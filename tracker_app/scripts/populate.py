# populate.py
import sqlite3
import random
from datetime import datetime, timedelta
import itertools
from tracker_app.core.db_module import init_all_databases
from tracker_app.config import DB_PATH

# ----------------------------
# Initialize DB
# ----------------------------
init_all_databases()
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ----------------------------
# Clear old data
# ----------------------------
cursor.execute("DELETE FROM sessions")
cursor.execute("DELETE FROM multi_modal_logs")
cursor.execute("DELETE FROM memory_decay")
cursor.execute("DELETE FROM metrics")
conn.commit()
print("Old data cleared.")

# ----------------------------
# Files / Topics for Knowledge Graph
# ----------------------------
files = [
    "intent_training_data_edge.csv", "intent_training_data_large.csv", "main.py", "merged_logs.csv",
    "multi_modal_logs_export.csv", "multi_modal_logs_invalid_rows.csv", "populate.py", "preflight_check.py",
    "sessions_export.csv", "sessions_invalid_rows.csv", "test_all.py", "test_audio.py", "test_dashboard.py",
    "test_db.py", "test_memory_graph.py", "tracker.db", "train_all_models.py", "train_models_from_logs.py",
    ".pytest_cache", "__pycache__", "core", "dashboard", "data", "htmlcov", "logs", "models", "results",
    "test_data", "tests", "training_data", ".coverage", "config.py", "install_dependencies.py", "clean.py",
    "config.json", "data_fetcher.py", "db.py", "debug_all_services.py", "debug_full_system.py", "demo.py",
    "demo_train_and_predict.py", "dummy_data.db", "export_all_data.py", "exported_data.json", "FKT 2.pptx",
    "flowRest.txt", "flowSessions.txt", "forgotten_knowledge.db", "generate_test_data.py", "insurance.csv",
    "migrate_audio_logs.py", "pokemon.csv", "preflight_check.py", "review_manager.py", "sample.wav",
    "seed_sessions.py", "session_classifier.joblib", "setup.py", "setup_sessions.py", "simulate_sessions.py",
    "test_endpoints.py", "test_review.py", "test_train.py", "tracker.db", "tracker.py", "tracking.db",
    "train_classifier.py", "validate_exported_data.py", ".history", "__pycache__", "csv_export", "services",
    "static", "templates", "venv", "activity.db", "activity_log.db", "all.json", "analytics.py", "app.py",
    "classifier.py", "classifier_config.json", "classifier_model.pkl", "1 (19).png", "1 (20).png", "1 (21).png",
    "1.certificatepg.docx", "2.docx", "3.docx", "AI.pdf", "algo.PNG", "Angle lines design.pptx", "Appflow.txt",
    "Architecture.PNG", "audio.PNG", "BCE PPT.pptx", "BCE.pdf", "BCE1.pptx", "BCEprax.pptx", "Book1.twb",
    "Capture.PNG", "Capture1.PNG", "Capture2.PNG", "Capturedesc.PNG", "Capturesteps.PNG", "Copilot_20251007_171501.png",
    "Copilot_20251007_171754.png", "DA_2026_Syllabus.pdf", "daikibo-telemetry-data.json", "data.PNG", "dc.PNG",
    "deepsite.avif", "deepsite-tic-toe-demo.webp", "def.txt", "Delinquency_prediction_dataset (1).xlsx",
    "Delinquency_prediction_dataset.pdf", "Delinquency_prediction_dataset.xlsx", "EDA_Example_Answer.docx",
    "EDA_SummaryReport.pdf", "EDA_SummaryReport_Template.docx", "example_answer_pptx.pptx",
    "Example_Business_Summary_Report.docx", "gentelella.webp", "Imputation_Guide_Handout.docx",
    "Introduction_merged.pdf", "mine.PNG", "newBCE.pptx", "ocr.PNG", "Op1.PNG", "Op2.PNG", "Pdfiot.docx",
    "Pdfiot.pdf", "Pdfiot1.pdf", "Presentation_Template.pptx", "progress and path.txt",
    "Project Report format.pdf", "QB.txt", "retention.PNG", "scikit-learn-docs.pdf", "SQLDocumentation.pdf",
    "Synopsis_with_changes.pdf", "Task 2_ModelPlan.pdf", "Task 2_ModelPlan_Template.docx",
    "Task 5 Equality Table.xlsx", "Task_2_Model_Plan_Example_Answer.docx", "Task4.pptx",
    "Tata_Data_Analytics_Glossary (1).docx", "tetris.PNG", "Timepass.png", "Transcript.txt",
    "Updated_Business_Summary_Report.pdf", "Updated_Business_Summary_Report_Template.docx",
    "WC 1 to 10 Experiment (1).pdf", "WC ASSIGNMENT 2.pdf", "wc ex 9.pdf", "Word-Letter-A4"
]

topics_cycle = itertools.cycle(files)

# ----------------------------
# Edge-case reference values for modalities
# ----------------------------
eye_states = ["attentive", "minor inattention", "sleeping", "occluded", "distracted", "unstable detection"]
audio_states = ["attentive", "ambient noise", "irrelevant speech", "no audio", "distorted", "multispeaker"]
ocr_states = ["perfect", "partial", "none", "low quality", "obstructed", "wrong"]
mouse_kb_states = ["active", "idle", "random", "rapid", "false positive", "automation"]

# ----------------------------
# Populate Sessions Table
# ----------------------------
print("Populating sessions table...")
for i in range(150):
    start = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
    duration_min = random.randint(5, 15)  # avg ~10
    end = start + timedelta(minutes=duration_min)
    intent = random.choice(["Read Docs", "Code", "Demo", "Train Model", "Review", "Test"])
    audio_label = random.choice(audio_states)
    cursor.execute("""
        INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        start, end, random.choice(["VS Code", "PowerPoint", "Browser", "Excel", "PyCharm"]),
        next(topics_cycle),
        round(random.uniform(0.1, 1.0), 2),
        random.randint(1, 50),
        audio_label,
        intent,
        round(random.uniform(0.5, 1.0), 2)
    ))

# ----------------------------
# Populate Multi-Modal Logs
# ----------------------------
print("Populating multi-modal logs table...")
for i in range(300):
    timestamp = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
    cursor.execute("""
        INSERT INTO multi_modal_logs (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        next(topics_cycle),
        random.choice(ocr_states),
        random.choice(audio_states),
        round(random.uniform(0, 1), 2),
        round(random.uniform(0, 1), 2),
        random.choice(["Read Docs", "Code", "Demo", "Train Model", "Review", "Test"]),
        round(random.uniform(0.5, 1.0), 2),
        round(random.uniform(0, 1), 2)
    ))

# ----------------------------
# Populate Memory Decay
# ----------------------------
print("Populating memory_decay table...")
for file in files:
    last_seen = datetime.now() - timedelta(days=random.randint(0, 30))
    cursor.execute("""
        INSERT INTO memory_decay (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        file,
        last_seen,
        round(random.uniform(0.2, 1.0), 2),
        random.randint(1, 10),
        datetime.now()
    ))

# ----------------------------
# Populate Metrics Table
# ----------------------------
print("Populating metrics table...")
for file in files:
    next_review = datetime.now() + timedelta(days=random.randint(1, 10))
    cursor.execute("""
        INSERT INTO metrics (concept, next_review_time, memory_score)
        VALUES (?, ?, ?)
    """, (
        file,
        next_review,
        round(random.uniform(0.2, 1.0), 2),
        
    ))

# ----------------------------
# Commit and Close
# ----------------------------
conn.commit()
conn.close()
print("Database populated successfully.")
