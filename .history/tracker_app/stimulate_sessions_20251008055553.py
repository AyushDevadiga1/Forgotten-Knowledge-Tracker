# simulate_sessions.py
import random
from datetime import datetime, timedelta
from core import db_module
import analytics  # your analytics.py

# -----------------------------
# CONFIG
# -----------------------------
NUM_SESSIONS = 10
EVENTS_PER_SESSION = 5
CONCEPTS = ["Python", "Memory", "AI", "Deep Learning", "Intent", "Analytics"]

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def random_time(base_time):
    return base_time + timedelta(seconds=random.randint(1, 300))

def random_interaction_rate():
    return round(random.uniform(0, 100), 2)

def random_attention_score():
    return round(random.uniform(0, 1), 2)

def random_intent_confidence():
    return round(random.uniform(0.5, 1.0), 2)

# -----------------------------
# MAIN SIMULATION
# -----------------------------
if __name__ == "__main__":
    print("🟢 Starting simulation...")

    # Step 1: Insert sessions
    for i in range(NUM_SESSIONS):
        start_ts = datetime.now() - timedelta(minutes=random.randint(0, 120))
        end_ts = random_time(start_ts)
        db_module.init_db()  # Ensure table exists
        conn = db_module.sqlite3.connect(db_module.DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO sessions (start_ts, end_ts, app_name, window_title, interaction_rate, interaction_count, audio_label, intent_label, intent_confidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                start_ts.strftime("%Y-%m-%d %H:%M:%S"),
                end_ts.strftime("%Y-%m-%d %H:%M:%S"),
                f"App_{i}",
                f"Window_{i}",
                random_interaction_rate(),
                random.randint(0, 10),
                random.choice(["silence", "speech"]),
                random.choice(["passive", "active"]),
                random_intent_confidence()
            )
        )
        session_id = c.lastrowid
        conn.commit()

        # Step 2: Insert multi-modal events for each session
        for j in range(EVENTS_PER_SESSION):
            db_module.log_multi_modal_event(
                window_title=f"Window_{i}",
                ocr_keywords="keyword1,keyword2",
                audio_label=random.choice(["audio1", "audio2"]),
                attention_score=random_attention_score(),
                interaction_rate=random_interaction_rate(),
                intent_label=random.choice(["intent1", "intent2"]),
                intent_confidence=random_intent_confidence(),
                memory_score=random.random(),
                source_module="simulation",
            )
        conn.close()

    # Step 3: Update memory decay & metrics
    analytics.update_memory_decay()
    analytics.update_metrics()

    # Step 4: Print analytics summary
    analytics.print_analytics_summary()

    print("✅ Simulation completed!")
