import os
import sqlite3
from datetime import datetime, timedelta
import json
from time import sleep

# -----------------------------
# Override DB_PATH for testing
# -----------------------------
from config import DB_PATH as ORIGINAL_DB_PATH
import config

DB_TEST_PATH = "data/test_tracker_sim.db"
os.makedirs("data", exist_ok=True)
if os.path.exists(DB_TEST_PATH):
    os.remove(DB_TEST_PATH)
config.DB_PATH = DB_TEST_PATH

# -----------------------------
# Import DB and tracker modules
# -----------------------------
from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.tracker import log_multi_modal

# -----------------------------
# 1. Initialize DB
# -----------------------------
init_db()
init_multi_modal_db()
init_memory_decay_db()

# -----------------------------
# 2. Mock data setup
# -----------------------------
window_title = "TestApp - Document1"
concepts = ["Python", "Memory", "Ebbinghaus"]
audio_labels = ["speech", "music", "silence"]
intent_labels = ["studying", "passive", "idle"]

G = get_graph()
add_concepts(concepts)

# -----------------------------
# 3. Simulate multiple sessions
# -----------------------------
num_sessions = 10
start_time = datetime.now() - timedelta(hours=24)  # start 24h ago

for i in range(num_sessions):
    timestamp = start_time + timedelta(hours=i * 2)  # every 2 hours

    # Randomize OCR keyword scores/counts
    ocr_keywords = {
        concept: {"score": 0.5 + 0.1*i, "count": i % 3 + 1}
        for concept in concepts
    }
    audio_label = audio_labels[i % len(audio_labels)]
    attention_score = 50 + 5*i
    interaction_rate = 2 + i
    intent_label = intent_labels[i % len(intent_labels)]
    intent_confidence = 0.7 + 0.03*i

    # Log multi-modal data
    log_multi_modal(
        window_title,
        ocr_keywords,
        audio_label,
        attention_score,
        interaction_rate,
        intent_label,
        intent_confidence,
        memory_score=0.0
    )

    # Update memory scores & forgetting curves
    for concept, info in ocr_keywords.items():
        last_review = timestamp - timedelta(hours=1 + i)
        mem_score = compute_memory_score(
            last_review,
            lambda_val=0.1,
            intent_conf=intent_confidence,
            attention_score=attention_score
        )
        next_review = schedule_next_review(last_review, mem_score, lambda_val=0.1)

        G.nodes[concept]['memory_score'] = mem_score
        G.nodes[concept]['next_review_time'] = next_review
        G.nodes[concept]['last_review'] = timestamp
        G.nodes[concept]['intent_conf'] = intent_confidence

        log_forgetting_curve(concept, last_review, observed_usage=info['count'])

    # Add edges
    add_edges(ocr_keywords, audio_label, intent_label)

    # Print session info
    print(f"Session {i+1}:")
    for concept in concepts:
        node = G.nodes[concept]
        print(f"  {concept}: memory_score={node['memory_score']:.2f}, next_review={node['next_review_time'].strftime('%H:%M')}")

    sleep(0.1)  # just to simulate delay

# -----------------------------
# 4. Verify DB entries
# -----------------------------
conn = sqlite3.connect(DB_TEST_PATH)
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM multi_modal_logs")
print("Total multi-modal logs:", c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM memory_decay")
print("Total memory_decay entries:", c.fetchone()[0])

conn.close()

# Reset DB_PATH
config.DB_PATH = ORIGINAL_DB_PATH
