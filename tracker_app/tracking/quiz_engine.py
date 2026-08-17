"""Micro-quiz interrupt: generates a contextual quiz from the weakest graph concept.

When idle for consecutive cycles, FKT quizzes the user via the dashboard
(Socket.IO) and feeds results straight into SM-2 scheduling.
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Optional
from tracker_app.learning.text_quality_validator import is_plausible_concept

logger = logging.getLogger("QuizEngine")

QUIZ_COOLDOWN_MINUTES = 20   # minimum gap between quizzes
IDLE_CYCLES_REQUIRED  = 12   # consecutive idle cycles (~60 s at 5 s cadence) before trigger
MIN_GRAPH_SIZE        = 4    # need at least this many concepts to quiz
# With webcam enabled, only interrupt when attention is at least this high:
# the user has paused but is still at the desk, so they can actually see and
# answer the modal. Firing on *low* attention would hit someone who zoned out
# or stepped away — the exact moment they will not see the question (10.3).
ATTENTION_PRESENT_MIN = 35

_last_quiz_time: Optional[datetime] = None


def reset_quiz_state():
    """Clear the quiz cooldown timer (H-1).

    Called when a fresh tracking session starts so a `_last_quiz_time` left
    over from a previous track_loop() run cannot censor the first quiz of
    the new session for the full QUIZ_COOLDOWN_MINUTES. Also used by tests
    for state isolation.
    """
    global _last_quiz_time
    _last_quiz_time = None


def record_quiz_broadcast():
    """Stamp the cooldown AFTER a quiz is actually delivered (M-6).

    generate_micro_quiz() no longer stamps the timer at generation time --
    the broadcast can fail (dashboard not running, client disconnected),
    and a quiz the user never saw must not consume the
    QUIZ_COOLDOWN_MINUTES window. Called by loop.py only once
    broadcast_micro_quiz() has succeeded.
    """
    global _last_quiz_time
    _last_quiz_time = datetime.utcnow()


# ─── Trigger logic ────────────────────────────────────────────────────────────

def should_show_quiz(
    idle_cycles: int,
    webcam_enabled: bool,
    attention_score: float,
    session_active: bool = True,
) -> bool:
    """
    Return True when a micro-quiz interrupt should fire.

    Conditions:
      - A study session is active (nobody is at the keyboard otherwise)
      - User has been idle for IDLE_CYCLES_REQUIRED+ consecutive cycles
        (a real pause, ~60 s — not between keystrokes)
      - At least QUIZ_COOLDOWN_MINUTES since the last quiz
      - If webcam enabled: attention is at least ATTENTION_PRESENT_MIN —
        the user paused but is still present. A quiz timed to a brief pause
        while attention stays moderate-to-high reaches someone able to answer
        it, instead of the old condition (attention < 35) which interrupted
        exactly when the user was away or mentally checked out.
      - If webcam disabled: idle_cycles is sufficient signal on its own
    """
    global _last_quiz_time

    if not session_active:
        return False   # never interrupt outside a study session

    if idle_cycles < IDLE_CYCLES_REQUIRED:
        return False

    if _last_quiz_time is not None:
        elapsed = (datetime.utcnow() - _last_quiz_time).total_seconds() / 60
        if elapsed < QUIZ_COOLDOWN_MINUTES:
            return False

    if webcam_enabled and attention_score < ATTENTION_PRESENT_MIN:
        return False   # user stepped away / zoned out — won't see the modal

    return True


# ─── Quiz generation ─────────────────────────────────────────────────────────

def generate_micro_quiz(graph) -> Optional[dict]:
    """
    Build a 4-option multiple-choice quiz from the weakest graph concept.

    Selection:
      - Prefers concepts with memory_score < 0.65 (weak memory)
      - Falls back to any string node if none qualify

    Distractors: top neighbours by edge weight (semantically close = hard distractors)

    Returns:
        {
            'concept':       str,   # concept being tested
            'question':      str,
            'correct_answer': str,
            'distractors':   [str, str, str],
            'all_options':   [str, str, str, str],  # shuffled
            'correct_index': int,
            'memory_score':  float,
        }
        or None if graph is too small.
    """
    nodes = [(n, d) for n, d in graph.nodes(data=True) if isinstance(n, str) and len(n) > 2 and is_plausible_concept(n)]
    if len(nodes) < MIN_GRAPH_SIZE:
        logger.debug(f"Graph too small for quiz ({len(nodes)} < {MIN_GRAPH_SIZE})")
        return None

    # Pick weakest concept
    weak = [x for x in nodes if x[1].get('memory_score', 0.5) < 0.65]
    pool = weak if weak else nodes
    pool.sort(key=lambda x: x[1].get('memory_score', 0.5))
    concept_name, concept_data = pool[0]

    # Build distractor list from neighbours
    neighbours = [
        n for n in graph.neighbors(concept_name)
        if isinstance(n, str) and n != concept_name and is_plausible_concept(n)
    ]
    neighbours.sort(
        key=lambda n: graph[concept_name][n].get('weight', 0),
        reverse=True
    )

    if len(neighbours) >= 3:
        distractors = neighbours[:3]
    else:
        other_names = [n for n, _ in nodes if n != concept_name]
        distractors = (neighbours + random.sample(
            [n for n in other_names if n not in neighbours],
            min(3 - len(neighbours), len(other_names) - len(neighbours))
        ))[:3]

    if len(distractors) < 3:
        logger.debug("Not enough distractors for quiz")
        return None

    all_options = [concept_name] + distractors[:3]
    random.shuffle(all_options)
    correct_index = all_options.index(concept_name)

    return {
        'concept':        concept_name,
        'question':       f"Which of these concepts have you been studying?",
        'correct_answer': concept_name,
        'distractors':    distractors[:3],
        'all_options':    all_options,
        'correct_index':  correct_index,
        'memory_score':   round(concept_data.get('memory_score', 0.5), 3),
        # dashboard (frontend) keys
        'options':        all_options,
        'difficulty':     ('easy' if concept_data.get('memory_score', 0.5) >= 0.65
                           else 'medium' if concept_data.get('memory_score', 0.5) >= 0.4
                           else 'hard'),
    }


# ─── Result recording ─────────────────────────────────────────────────────────

def record_quiz_result(concept: str, was_correct: bool):
    """
    Feed quiz result into SM-2 scheduling.
    Correct = quality 4 (good recall), wrong = quality 0 (complete miss).
    """
    quality = 4 if was_correct else 0
    try:
        from tracker_app.learning.concept_scheduler import get_scheduler
        scheduler = get_scheduler()
        scheduler.schedule_next_review(concept, quality=quality)
        logger.info(
            f"Quiz: '{concept}' {'correct' if was_correct else 'wrong'} "
            f"→ quality {quality} fed to SM-2"
        )
    except Exception as e:
        logger.error(f"Failed to record quiz result for '{concept}': {e}")
