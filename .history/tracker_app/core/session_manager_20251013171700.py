# ==========================================================
# core/session_manager_v4.py | IEEE v4 Async Multi-Modal
# ==========================================================
"""
Session Manager v4 (IEEE-ready Async)
-------------------------------------
- Fully async session creation, updates, and DB logging
- Tracks attention, audio, intent, interaction, memory
- Temporal smoothing over HISTORY_LENGTH frames
- Syncs multi-modal signals with Knowledge Graph
- Structured logging & fault-tolerant
"""

import asyncio
import sqlite3
import logging
from datetime import datetime
from collections import deque
from typing import Dict, Any, Optional, List

from config import DB_PATH, HISTORY_LENGTH
from core.db_module import log_multi_modal_event
from core.knowledge_graph import get_graph

# ==========================================================
# LOGGER SETUP
# ==========================================================
logger = logging.getLogger("SessionManagerV4")
if not logger.handlers:
    handler = logging.FileHandler("logs/session_manager_v4.log")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(funcName)s | %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ==========================================================
# TEMPORAL SMOOTHING HISTORY
# ==========================================================
_attention_history: deque = deque(maxlen=HISTORY_LENGTH)
_interaction_history: deque = deque(maxlen=HISTORY_LENGTH)
_memory_history: deque = deque(maxlen=HISTORY_LENGTH)

def _smooth(values: deque) -> float:
    return float(sum(values) / len(values)) if values else 0.0

# ==========================================================
# SESSION MANAGEMENT
# ==========================================================
def create_session() -> Dict[str, Any]:
    """Initialize a new session with default values"""
    now = datetime.now()
    session: Dict[str, Any] = {
        "window_title": "",
        "interaction_rate": 0,
        "ocr_keywords": [],
        "audio_label": "silence",
        "audio_confidence": 0.0,
        "attention_score": 0.0,
        "intent_label": "",
        "intent_confidence": 0.0,
        "memory_score": 0.0,
        "last_review": now,
        "next_review": now,
        "start_time": now,
        "last_update": now
    }
    logger.info("Created new session")
    return session

# ==========================================================
# SYNC SESSION TO KNOWLEDGE GRAPH
# ==========================================================
def sync_session_to_graph(session: Dict[str, Any]) -> None:
    try:
        G = get_graph()
        concept = session.get("window_title")
        if concept:
            if concept in G:
                G.nodes[concept]['attention_score'] = session.get("attention_score", 0.0)
                G.nodes[concept]['memory_score'] = session.get("memory_score", 0.0)
                G.nodes[concept]['last_seen_ts'] = datetime.now().isoformat()
            else:
                G.add_node(
                    concept,
                    type="Concept",
                    embedding=None,
                    memory_score=session.get("memory_score", 0.0),
                    attention_score=session.get("attention_score", 0.0),
                    count=1,
                    source="SessionManagerV4",
                    created_at=datetime.now().isoformat(),
                    last_seen_ts=datetime.now().isoformat()
                )
        logger.info(f"Session synced to KG: '{concept}'")
    except Exception as e:
        logger.error(f"[SessionManagerV4] Graph sync failed: {e}", exc_info=True)

# ==========================================================
# SESSION UPDATE
# ==========================================================
def update_session(session: Dict[str, Any], key: str, value: Any, log_db: bool = True) -> None:
    """Update session field, smooth temporal metrics, sync to KG, optionally log to DB"""
    try:
        session[key] = value
        session["last_update"] = datetime.now()

        # Temporal smoothing
        if key == "attention_score":
            _attention_history.append(float(value))
            session["attention_score"] = _smooth(_attention_history)
        elif key == "interaction_rate":
            _interaction_history.append(float(value))
            session["interaction_rate"] = _smooth(_interaction_history)
        elif key == "memory_score":
            _memory_history.append(float(value))
            session["memory_score"] = _smooth(_memory_history)

        # Sync to KG
        sync_session_to_graph(session)

        logger.info(f"Session updated: {key}={value}")

        # Async DB logging
        if log_db:
            asyncio.create_task(log_multi_modal_event(
                window_title=session.get("window_title", ""),
                ocr_keywords=", ".join(session.get("ocr_keywords", [])),
                audio_label=session.get("audio_label", ""),
                attention_score=session.get("attention_score", 0.0),
                interaction_rate=session.get("interaction_rate", 0.0),
                intent_label=session.get("intent_label", ""),
                intent_confidence=session.get("intent_confidence", 0.0),
                memory_score=session.get("memory_score", 0.0),
                source_module="SessionManagerV4"
            ))
    except Exception as e:
        logger.error(f"[SessionManagerV4] Failed to update session: {e}", exc_info=True)

# ==========================================================
# FULL SESSION LOG
# ==========================================================
def log_session_to_db(session: Dict[str, Any]) -> None:
    """Persist full session state to the DB 'sessions' table"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO sessions (
                start_ts, end_ts, app_name, window_title, interaction_rate,
                audio_label, intent_label, intent_confidence,
                attention_score, memory_score, last_review, next_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                session.get("start_time", datetime.now()).isoformat(),
                session.get("last_update", datetime.now()).isoformat(),
                session.get("window_title", ""),
                session.get("window_title", ""),
                session.get("interaction_rate", 0),
                session.get("audio_label", ""),
                session.get("intent_label", ""),
                session.get("intent_confidence", 0.0),
                session.get("attention_score", 0.0),
                session.get("memory_score", 0.0),
                session.get("last_review", datetime.now()).isoformat(),
                session.get("next_review", datetime.now()).isoformat()
            ))
            logger.info("Full session logged to DB successfully")
    except Exception as e:
        logger.error(f"[SessionManagerV4] Failed to log session to DB: {e}", exc_info=True)

# ==========================================================
# ASYNC WRAPPERS
# ==========================================================
async def async_update_session(session: Dict[str, Any], key: str, value: Any):
    await asyncio.to_thread(update_session, session, key, value)

async def async_log_session(session: Dict[str, Any]):
    await asyncio.to_thread(log_session_to_db, session)

# ==========================================================
# SELF-TEST
# ==========================================================
if __name__ == "__main__":
    import asyncio
    session = create_session()
    asyncio.run(async_update_session(session, "window_title", "Photosynthesis"))
    asyncio.run(async_update_session(session, "interaction_rate", 12))
    asyncio.run(async_update_session(session, "ocr_keywords", ["chlorophyll", "light reaction"]))
    asyncio.run(async_update_session(session, "memory_score", 0.55))
    asyncio.run(async_log_session(session))
    print("✅ Session created and logged successfully")
    print(session)
