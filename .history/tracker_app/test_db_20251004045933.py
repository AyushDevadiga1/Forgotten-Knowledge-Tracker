import os
import sqlite3
from datetime import datetime, timedelta
import json
from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
from core.memory_model import compute_memory_score, schedule_next_review, log_forgetting_curve
from core.knowledge_graph import add_concepts, get_graph, add_edges
from core.tracker import log_multi_modal

# Override DB_PATH in config temporarily for testing
from config import DB_PATH as ORIGINAL_DB_PATH
import config
config.DB_PATH = DB_TEST_PATH

# -----------------------------
# 1. Setup DB
# -----------------------------
if os.path.exists(DB_TEST_PATH):
    os.remove(DB_TEST_PATH)  # clean slate

init_db()
init_multi_modal_db()
init_memory_decay_db()

# -----------------------------
# 2. Create mock session & multi-modal data
# -----------------------------
window_title = "TestApp - Document1"
ocr_keywords = {
    "Python": {"score": 0.8, "count": 2},
    "Memory": {"score": 0.6, "count": 1}
}
audio_label = "speech"
attention_score = 80
interaction_rate = 5
intent_label = "studying"
intent_confidence = 0.9

# Log multi-modal data
log_multi_modal(
    window_title,
    ocr_keywords,
    audio_label,
    attention_score,
    interaction_rate,
    intent_label,
    intent_confidence,
    memory_score=0.0  # placeholder
)

# -----------------------------
# 3. Compute memory scores and schedule reviews
# -----------------------------
G = get_graph()
add_concepts(list(ocr_keywords.keys()))

for concept, info in ocr_keywords.items():
    last_review = datetime.now() - timedelta(hours=2)
    mem_score = compute_memory_score(last_review, lambda_val=0.1,
                                     intent_conf=intent_confidence,
                                     attention_score=attention_score)
    next_review = schedule_next_review(last_review, mem_score, lambda_val=0.1)

    G.nodes[concept]['memory_score'] = mem_score
    G.nodes[concept]['next_review_time'] = next_review
    G.nodes[concept]['last_review'] = datetime.now()
    G.nodes[concept]['intent_conf'] = intent_confidence

    # Log forgetting curve
    pred_recall = log_forgetting_curve(concept, last_review, observed_usage=info['count'])

# Add edges
add_edges(ocr_keywords, audio_label, intent_label)

# -----------------------------
# 4. Verify DB entries
# -----------------------------
conn = sqlite3.connect(DB_TEST_PATH)
c = conn.cursor()

# Multi-modal logs
c.execute("SELECT * FROM multi_modal_logs")
multi_modal_rows = c.fetchall()
assert len(multi_modal_rows) == 1, "Multi-modal log not inserted!"

# Memory decay logs
c.execute("SELECT * FROM memory_decay")
decay_rows = c.fetchall()
assert len(decay_rows) == len(ocr_keywords), "Memory decay entries missing!"

conn.close()

# -----------------------------
# 5. Verify Knowledge Graph
# -----------------------------
graph_nodes = get_graph().nodes()
assert "Python" in graph_nodes, "Python node missing from knowledge graph!"
assert "Memory" in graph_nodes, "Memory node missing from knowledge graph!"
assert graph_nodes["Python"]['memory_score'] > 0, "Memory score not set!"

print("✅ Step 3 test passed: DB, memory scores, forgetting curve, and knowledge graph work correctly.")

# Reset DB_PATH
config.DB_PATH = ORIGINAL_DB_PATH
