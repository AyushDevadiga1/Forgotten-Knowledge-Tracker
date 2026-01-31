import sqlite3
import os
import random
import string
from datetime import datetime, timedelta

from config import DB_PATH

# -----------------------------
# Utility Functions
# -----------------------------
def random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_time(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def random_float(low=0, high=1):
    return round(random.uniform(low, high), 3)

# -----------------------------
# Files / Topics to Populate
# -----------------------------
# Your project files
project_files = [
    "main.py","populate.py","tracker.db","train_all_models.py","test_all.py",
    "config.py","data_fetcher.py","demo.py","FKT 2.pptx"
]

# Dump folder files (filenames only)
dump_files = [
    "1 (19).png","1 (20).png","1 (21).png","1.certificatepg.docx","2.docx","3.docx",
    "AI.pdf","algo.PNG","Angle lines design.pptx","Appflow.txt","Architecture.PNG",
    "audio.PNG","BCE PPT.pptx","BCE.pdf","BCE1.pptx","BCEprax.pptx","Book1.twb",
    "Capture.PNG","Capture1.PNG","Capture2.PNG","Capturedesc.PNG","Capturesteps.PNG",
    "Copilot_20251007_171501.png","Copilot_20251007_171754.png","DA_2026_Syllabus.pdf",
    "daikibo-telemetry-data.json","data.PNG","dc.PNG","deepsite.avif",
    "deepsite-tic-toe-demo.webp","def.txt",
    "Delinquency_prediction_dataset (1).xlsx","Delinquency_prediction_dataset.pdf",
    "Delinquency_prediction_dataset.xlsx","EDA_Example_Answer.docx",
    "EDA_SummaryReport.pdf","EDA_SummaryReport_Template.docx",
    "example_answer_pptx.pptx","Example_Business_Summary_Report.docx",
    "gentelella.webp","Imputation_Guide_Handout.docx","Introduction_merged.pdf",
    "mine.PNG","newBCE.pptx","ocr.PNG","Op1.PNG","Op2.PNG",
    "Pdfiot.docx","Pdfiot.pdf","Pdfiot1.pdf","Presentation_Template.pptx",
    "progress and path.txt","Project Report format.pdf","QB.txt","retention.PNG",
    "scikit-learn-docs.pdf","SQLDocumentation.pdf","Synopsis_with_changes.pdf",
    "Task 2_ModelPlan.pdf","Task 2_ModelPlan_Template.docx",
    "Task 5 Equality Table.xlsx","Task_2_Model_Plan_Example_Answer.docx",
    "Task4.pptx","Tata_Data_Analytics_Glossary (1).docx","tetris.PNG","Timepass.png",
    "Transcript.txt","Updated_Business_Summary_Report.pdf",
    "Updated_Business_Summary_Report_Template.docx",
    "WC 1 to 10 Experiment (1).pdf","WC ASSIGNMENT 2.pdf","wc ex 9.pdf",
    "Word-Letter-A4","1 (1).jpg","1 (1).png","1 (2).jpg","1 (3).jpg","1 (8).png",
    "1 (9).png","1 (10).png","1 (11).png","1 (12).png","1 (13).png","1 (14).png",
    "1 (15).png","1 (16).png","1 (17).png","1 (18).png"
]

# Combine all concepts
all_concepts = list(set(project_files + dump_files))

# Ensure at least 100 topics
while len(all_concepts) < 100:
    all_concepts.append(f"Random_Topic_{random_string(5)}")

# -----------------------------
# Connect to Database
# -----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# Populate sessions table
# -----------------------------
print("Populating sessions table...")
apps = ["VS Code", "Chrome", "PowerPoint", "Word", "Excel", "PyCharm", "Jupyter"]
for _ in range(300):
    start_ts = random_time(datetime.now() - timedelta(days=30), datetime.now())
    end_ts = start_ts + timedelta(minutes=random.randint(5, 120))
    app_name = random.choice(apps)
    window_title = f"{random.choice(all_concepts)} - {app_name}"
    interaction_rate = random_float(0, 1)
    interaction_count = random.randint(1, 100)
    audio_label = random.choice(["N/A", "Talking", "Listening", "Music"])
    intent_label = random.choice(all_concepts)
    intent_confidence = random_float(0.5, 1.0)
    
    cursor.execute("""
        INSERT INTO sessions
        (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence))

# -----------------------------
# Populate multi_modal_logs table
# -----------------------------
print("Populating multi-modal logs table...")
for _ in range(500):
    timestamp = random_time(datetime.now() - timedelta(days=30), datetime.now())
    window_title = f"{random.choice(all_concepts)} Window"
    ocr_keywords = random.choice(all_concepts)
    audio_label = random.choice(["Talking", "Music", "Silence", "N/A"])
    attention_score = random_float(0, 1)
    interaction_rate = random_float(0, 1)
    intent_label = random.choice(all_concepts)
    intent_confidence = random_float(0.5, 1.0)
    memory_score = random_float(0, 1)

    cursor.execute("""
        INSERT INTO multi_modal_logs
        (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence, memory_score))

# -----------------------------
# Populate memory_decay table
# -----------------------------
print("Populating memory_decay table...")
for concept in all_concepts:
    for _ in range(random.randint(5,10)):
        last_seen_ts = random_time(datetime.now() - timedelta(days=30), datetime.now())
        predicted_recall = random_float(0, 1)
        observed_usage = random.randint(0, 20)
        updated_at = last_seen_ts + timedelta(days=random.randint(0, 5))
        cursor.execute("""
            INSERT INTO memory_decay
            (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (concept, last_seen_ts, predicted_recall, observed_usage, updated_at))

# -----------------------------
# Populate metrics table
# -----------------------------
print("Populating metrics table...")
for concept in all_concepts:
    next_review_time = datetime.now() + timedelta(days=random.randint(1, 15))
    memory_score = random_float(0, 1)
    last_updated = datetime.now() - timedelta(days=random.randint(0, 5))
    cursor.execute("""
        INSERT INTO metrics
        (concept, next_review_time, memory_score, last_updated)
        VALUES (?, ?, ?, ?)
    """, (concept, next_review_time, memory_score, last_updated))

# Commit changes
conn.commit()
conn.close()
print("Database population completed successfully!")
