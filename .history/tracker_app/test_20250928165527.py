# tests/test_integration.py
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

# set import path to your tracker_app if needed
# import sys; sys.path.append("tracker_app")

from core.db_module import init_db, encrypt_data, decrypt_data, log_session_data, log_metric
from core.session_manager import create_session, update_session
from core.knowledge_graph import add_concepts, get_graph, sync_db_to_graph
from core.memory_model import compute_memory_score, schedule_next_review

# ---- Test helper: create a temp DB and override config.DB_PATH ----
import config
ORIG_DB_PATH = config.DB_PATH

@pytest.fixture(scope="function")
@pytest.fixture(scope="function")
def temp_db(monkeypatch):
    import tempfile, shutil, os
    import config
    import sqlite3
    from core.db_module import init_db

    tmpdir = tempfile.mkdtemp(prefix="fkt_test_")
    tmp_db = os.path.join(tmpdir, "sessions_test.db")

    # Patch DB_PATH
    monkeypatch.setattr(config, "DB_PATH", tmp_db)

    # Call init_db **after monkeypatch** to ensure tables go to temp DB
    init_db()

    yield tmp_db

    shutil.rmtree(tmpdir)

# ---- Test: DB init and basic session logging ----
def test_log_session_and_fetch(temp_db):
    # create session snapshot
    s = create_session()
    update_session(s, "window_title", "Test App - Document")
    update_session(s, "interaction_rate", 12)
    update_session(s, "ocr_keywords", ["photosynthesis", "mitosis"])
    update_session(s, "audio_label", "speech")
    update_session(s, "attention_score", 1)
    update_session(s, "intent_label", "study", save_to_db=False)
    # write snapshot
    log_session_data(s)

    # read raw rows from sqlite to verify storage
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("SELECT start_ts, end_ts, app_name, window_title, interaction_rate FROM sessions ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    assert row is not None, "No row written to sessions"
    start_ts, end_ts, app_blob, win_blob, ir = row

    # If encryption used, decrypt; otherwise encrypt_data/decrypt_data are pass-through
    app_dec = decrypt_data(app_blob)
    win_dec = decrypt_data(win_blob)
    assert "Test App" in app_dec or "Test App" in win_dec
    assert int(ir) == 12

# ---- Test: encryption roundtrip (if enabled) ----
def test_encrypt_decrypt_roundtrip():
    sample = "Sensitive Window Title"
    enc = encrypt_data(sample)
    dec = decrypt_data(enc)
    assert dec == sample

# ---- Test: knowledge graph integration ----
def test_knowledge_graph_and_memory(temp_db):
    # Add some concepts
    concepts = ["photosynthesis", "mitosis", "cell division"]
    add_concepts(concepts)
    G = get_graph()
    for c in concepts:
        assert c in G.nodes, f"{c} not in graph"

    # simulate memory scoring for one concept
    concept = "photosynthesis"
    last_review = datetime.now() - timedelta(days=2)
    lambda_val = 0.1
    intent_conf = 0.9
    attention_score = 1
    audio_conf = 1.0

    mem_score = compute_memory_score(last_review, lambda_val, intent_conf, attention_score, audio_conf)
    assert isinstance(mem_score, float)
    # schedule next review
    next_review = schedule_next_review(last_review, mem_score, lambda_val)
    assert isinstance(next_review, datetime)

    # persist metric
    log_metric(concept, mem_score, next_review)

    # verify metrics row exists in DB
    conn = sqlite3.connect(temp_db)
    c = conn.cursor()
    c.execute("SELECT concept, memory_score, next_review_time FROM metrics WHERE memory_score IS NOT NULL ORDER BY id DESC LIMIT 1")
    mrow = c.fetchone()
    conn.close()
    assert mrow is not None
    concept_dec = decrypt_data(mrow[0])
    assert concept_dec == concept

# ---- Test: sync_db_to_graph does not crash and graph contains metric node info ----
def test_sync_db_to_graph_and_node_attrs(temp_db):
    # ensure sync will read the metrics and annotate graph nodes
    sync_db_to_graph()
    G = get_graph()
    # nodes exist, and at least one node has memory_score attribute
    found = False
    for n in G.nodes:
        if 'memory_score' in G.nodes[n]:
            found = True
            break
    assert found, "No node has memory_score after sync_db_to_graph"
