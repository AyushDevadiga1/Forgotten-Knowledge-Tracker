# tools/populate.py — FKT 2.0 Phase 13
# Fixed: was seeding DB with filename strings (.png, .docx, etc.)
# Now uses real academic concept names across multiple domains.

import random
from datetime import datetime, timedelta
from tracker_app.db.db_module import init_all_databases
from tracker_app.config import DB_PATH
import sqlite3

init_all_databases()
conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Clear old data
for table in ("sessions", "multi_modal_logs", "memory_decay", "metrics", "tracked_concepts", "concept_encounters"):
    try:
        cursor.execute(f"DELETE FROM {table}")
    except Exception:
        pass
conn.commit()
print("Old data cleared.")

# Real academic concepts across multiple domains
CONCEPTS = [
    # ML / AI
    "neural network", "backpropagation", "gradient descent", "overfitting",
    "regularization", "dropout", "attention mechanism", "transformer",
    "convolutional neural network", "recurrent neural network", "embedding",
    "softmax", "cross entropy", "batch normalization", "learning rate",
    # CS fundamentals
    "recursion", "dynamic programming", "binary search", "hash table",
    "quicksort", "merge sort", "binary tree", "graph traversal", "big-o notation",
    "stack", "queue", "linked list", "heap", "trie",
    # Biology
    "photosynthesis", "cellular respiration", "mitosis", "meiosis", "dna replication",
    "protein synthesis", "natural selection", "evolution", "osmosis", "diffusion",
    # Math
    "eigenvalue", "matrix multiplication", "derivatives", "integration",
    "probability", "bayesian inference", "hypothesis testing", "normal distribution",
    # Memory science
    "spaced repetition", "ebbinghaus forgetting curve", "working memory",
    "cognitive load", "active recall", "interleaving", "mnemonics",
]

intents = ["studying", "passive", "idle"]
audios  = ["speech", "music", "silence", "unknown"]

# Sessions
for i in range(100):
    start = datetime.utcnow() - timedelta(days=random.randint(0,30), hours=random.randint(0,23))
    end   = start + timedelta(minutes=random.randint(5, 45))
    cursor.execute("""
        INSERT INTO sessions
        (start_ts, end_ts, app_name, window_title, interaction_rate,
         interaction_count, audio_label, intent_label, intent_confidence)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        start.isoformat(), end.isoformat(),
        random.choice(["VS Code", "Chrome", "PyCharm", "Obsidian"]),
        random.choice(CONCEPTS),
        round(random.uniform(0.1, 15.0), 2),
        random.randint(1, 200),
        random.choice(audios),
        random.choice(intents),
        round(random.uniform(0.55, 0.99), 2),
    ))

# Multi-modal logs
for i in range(200):
    ts = datetime.utcnow() - timedelta(days=random.randint(0,30), hours=random.randint(0,23))
    cursor.execute("""
        INSERT INTO multi_modal_logs
        (timestamp, window_title, ocr_keywords, audio_label,
         attention_score, interaction_rate, intent_label, intent_confidence, memory_score)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        ts.isoformat(),
        random.choice(CONCEPTS),
        str(random.sample(CONCEPTS, min(5, len(CONCEPTS)))),
        random.choice(audios),
        round(random.uniform(15, 95), 1),
        round(random.uniform(0, 20), 2),
        random.choice(intents),
        round(random.uniform(0.55, 0.99), 2),
        round(random.uniform(0.2, 1.0), 3),
    ))

# Tracked concepts
now = datetime.utcnow()
for concept in CONCEPTS:
    last_seen   = now - timedelta(days=random.randint(0, 20))
    next_review = last_seen + timedelta(days=random.randint(1, 10))
    cursor.execute("""
        INSERT OR IGNORE INTO tracked_concepts
        (concept, first_seen, last_seen, frequency_count, relevance_score,
         status, interval, memory_strength, next_review,
         attention_at_encoding, lambda_personalised)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        concept,
        (now - timedelta(days=random.randint(5, 60))).isoformat(),
        last_seen.isoformat(),
        random.randint(1, 20),
        round(random.uniform(0.3, 0.95), 3),
        "discovered",
        random.randint(1, 14),
        round(random.uniform(1.3, 3.5), 3),
        next_review.isoformat(),
        round(random.uniform(20, 90), 1),
        round(random.uniform(0.05, 0.15), 4),
    ))

# Memory decay
for concept in CONCEPTS:
    last_seen = now - timedelta(days=random.randint(0, 30))
    cursor.execute("""
        INSERT OR IGNORE INTO memory_decay
        (keyword, last_seen_ts, predicted_recall, observed_usage, updated_at)
        VALUES (?,?,?,?,?)
    """, (
        concept,
        last_seen.isoformat(),
        round(random.uniform(0.2, 1.0), 3),
        random.randint(1, 15),
        now.isoformat(),
    ))

conn.commit()
conn.close()
print(f"Database seeded with {len(CONCEPTS)} real academic concepts.")
print("Sessions: 100 | Logs: 200 | Concepts: tracked + memory decay")
