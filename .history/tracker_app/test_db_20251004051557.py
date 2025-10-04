import os
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from time import sleep
from plyer import notification

# -----------------------------
# Override DB_PATH for testing
# -----------------------------
from config import DB_PATH as ORIGINAL_DB_PATH
import config

DB_TEST_PATH = "data/test_tracker_plot.db"
os.makedirs("data", exist_ok=True)
if os.path.exists(DB_TEST_PATH):
    os.remove(DB_TEST_PATH)
config.DB_PATH = DB_TEST_PATH

# -----------------------------
# Import DB and tracker modules
# -----------------------------
from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve, MEMORY_THRESHOLD
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

# Prepare for plotting
plot_data = {concept: {"times": [], "memory_scores": []} for concept in concepts}

# -----------------------------
# 3. Simulate multiple sessions realistically
# -----------------------------
num_sessions = 10
start_time = datetime.now() - timedelta(hours=24)  # 24h ago
lambda_val = 0.1

for i in range(num_sessions):
    timestamp = start_time + timedelta(hours=i * 2)  # every 2 hours

    # Random OCR keyword info
    ocr_keywords = {concept: {"score": 0.5, "count": 1} for concept in concepts}
    audio_label = audio_labels[i % len(audio_labels)]
    attention_score = 50
    interaction_rate = 2 + i
    intent_label = intent_labels[i % len(intent_labels)]
    intent_confidence = 0.8

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
    for concept in concepts:
        last_review = G.nodes[concept].get('last_review', start_time - timedelta(hours=1))
        mem_score = compute_memory_score(
            last_review,
            lambda_val=lambda_val,
            intent_conf=intent_confidence,
            attention_score=attention_score
        )

        # Schedule next review
        next_review = schedule_next_review(last_review, mem_score, lambda_val=lambda_val)
        G.nodes[concept]['memory_score'] = mem_score
        G.nodes[concept]['next_review_time'] = next_review

        # Only "review" if session mentions concept
        if concept in ocr_keywords:
            G.nodes[concept]['last_review'] = timestamp
            mem_score += 0.1  # small boost for active session
            if mem_score > 1.0:
                mem_score = 1.0
            G.nodes[concept]['memory_score'] = mem_score

        # Log forgetting curve in DB
        log_forgetting_curve(concept, last_review, observed_usage=ocr_keywords[concept]['count'])

        # Notifications simulation
        if mem_score < MEMORY_THRESHOLD:
            print(f"🔔 Notification: Review '{concept}' (memory score={mem_score:.2f})")
            # Optionally use plyer notification
            # notification.notify(title="Time to Review!", message=f"Concept: {concept}\nMemory Score: {mem_score:.2f}", timeout=2)

        # Store for plotting
        plot_data[concept]["times"].append(timestamp)
        plot_data[concept]["memory_scores"].append(mem_score)

    # Add edges
    add_edges(ocr_keywords, audio_label, intent_label)

    sleep(0.05)

# -----------------------------
# 4. Plot realistic forgetting curves
# -----------------------------
plt.figure(figsize=(10,6))
for concept, data in plot_data.items():
    plt.plot(data["times"], data["memory_scores"], marker='o', label=concept)
plt.xlabel("Time")
plt.ylabel("Memory Score")
plt.title("Simulated Memory Decay / Forgetting Curve")
plt.ylim(0,1.05)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# -----------------------------
# 5. DB checks
# -----------------------------
conn = sqlite3.connect(DB_TEST_PATH)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM multi_modal_logs")
print("Total multi-modal logs:", c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM memory_decay")
print("Total memory_decay entries:", c.fetchone()[0])
conn.close()

# -----------------------------
# 6. Knowledge Graph checks
# -----------------------------
for concept in concepts:
    node = G.nodes[concept]
    assert 'memory_score' in node
    assert 'next_review_time' in node
print("✅ Knowledge graph nodes OK")

# Reset DB_PATH
config.DB_PATH = ORIGINAL_DB_PATH
