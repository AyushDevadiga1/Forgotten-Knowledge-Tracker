# analytics.py
"""
Analytics & Memory Update Module
--------------------------------
- Computes memory decay
- Updates metrics table
- Generates simple reports
"""

import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH
import logging

# -----------------------------
# LOGGER SETUP
# -----------------------------
logging.basicConfig(
    filename="logs/analytics.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -----------------------------
# Memory Decay Update
# -----------------------------
def update_memory_decay():
    """
    Calculate updated memory decay for all concepts based on multi_modal_logs.
    Uses simple exponential decay for demo purposes.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Get all multi-modal events
        c.execute("SELECT ocr_keywords, timestamp FROM multi_modal_logs")
        events = c.fetchall()

        memory_updates = {}
        decay_rate = 0.8  # simple decay factor for demonstration

        for keywords, ts in events:
            if not keywords:
                continue
            for concept in [k.strip() for k in keywords.split(',')]:
                last_seen = memory_updates.get(concept, None)
                if last_seen:
                    # Simple decay calculation
                    hours_passed = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
                    memory_updates[concept] = last_seen * (decay_rate ** hours_passed)
                else:
                    memory_updates[concept] = 1.0  # full memory score initially

        # Update memory_decay table
        for concept, score in memory_updates.items():
            c.execute("""
                INSERT INTO memory_decay (concept, last_seen_ts, predicted_recall, observed_usage, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (concept, datetime.now().isoformat(), score, 1, datetime.now().isoformat()))
        
        conn.commit()
        logging.info("Memory decay updated successfully.")
        conn.close()
        print("✅ Memory decay updated.")
    except Exception as e:
        logging.error(f"Failed to update memory decay: {e}")


# -----------------------------
# Metrics Update
# -----------------------------
def update_metrics():
    """
    Updates the metrics table based on latest memory_decay entries
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Fetch latest memory_decay entries
        c.execute("SELECT concept, predicted_recall FROM memory_decay")
        memory_data = c.fetchall()

        for concept, score in memory_data:
            next_review = datetime.now() + timedelta(hours=24)  # example: next review 24 hrs later
            c.execute("""
                INSERT INTO metrics (concept, memory_score, next_review_time)
                VALUES (?, ?, ?)
            """, (concept, score, next_review.isoformat()))
        
        conn.commit()
        logging.info("Metrics table updated successfully.")
        conn.close()
        print("✅ Metrics table updated.")
    except Exception as e:
        logging.error(f"Failed to update metrics: {e}")


# -----------------------------
# Simple Analytics Report
# -----------------------------
def generate_report():
    """
    Prints summary of sessions and memory trends
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Total sessions
        c.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = c.fetchone()[0]

        # Average interaction rate
        c.execute("SELECT AVG(interaction_rate) FROM sessions")
        avg_interaction = c.fetchone()[0]

        # Total unique concepts in memory_decay
        c.execute("SELECT COUNT(DISTINCT concept) FROM memory_decay")
        unique_concepts = c.fetchone()[0]

        print("\n📊 Analytics Report")
        print(f"Total Sessions: {total_sessions}")
        print(f"Average Interaction Rate: {avg_interaction:.2f}")
        print(f"Unique Concepts Tracked: {unique_concepts}\n")

        conn.close()
    except Exception as e:
        logging.error(f"Failed to generate analytics report: {e}")


# -----------------------------
# SELF-TEST
# -----------------------------
if __name__ == "__main__":
    update_memory_decay()
    update_metrics()
    generate_report()
