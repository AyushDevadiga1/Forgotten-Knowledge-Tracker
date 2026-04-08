# tracking/quiz_engine.py — FKT 2.0 Phase 7
# Micro-Quiz Interrupt System — novel feature.
#
# When idle for 3+ consecutive cycles, FKT generates a contextual quiz
# from the weakest concept in the knowledge graph and broadcasts it
# to the dashboard via Socket.IO.
# Results feed directly into SM-2 scheduling.

import random
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("QuizEngine")

QUIZ_COOLDOWN_MINUTES = 20   # minimum gap between quizzes
IDLE_CYCLES_REQUIRED  = 3    # how many consecutive idle cycles before trigger
MIN_GRAPH_SIZE        = 4    # need at least this many concepts to quiz

_last_quiz_time: Optional[datetime] = None


# ─── Trigger logic ────────────────────────────────────────────────────────────

def should_show_quiz(
    idle_cycles: int,
    webcam_enabled: bool,
    attention_score: float,
) -> bool:
    """
    Return True when a micro-quiz interrupt should fire.

    Conditions:
      - User has been idle for IDLE_CYCLES_REQUIRED+ consecutive cycles
      - At least QUIZ_COOLDOWN_MINUTES since the last quiz
      - If webcam enabled: attention score < 35 (user is away / zoned out)
      - If webcam disabled: idle_cycles is sufficient signal on its own
    """
    global _last_quiz_time

    if idle_cycles < IDLE_CYCLES_REQUIRED:
        return False

    if _last_quiz_time is not None:
        elapsed = (datetime.utcnow() - _last_quiz_time).total_seconds() / 60
        if elapsed < QUIZ_COOLDOWN_MINUTES:
            return False

    if webcam_enabled and attention_score > 35:
        return False   # user is actually paying attention

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
    global _last_quiz_time

    nodes = [(n, d) for n, d in graph.nodes(data=True) if isinstance(n, str) and len(n) > 2]
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
        if isinstance(n, str) and n != concept_name
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

    _last_quiz_time = datetime.utcnow()

    return {
        'concept':        concept_name,
        'question':       f"Which of these concepts have you been studying?",
        'correct_answer': concept_name,
        'distractors':    distractors[:3],
        'all_options':    all_options,
        'correct_index':  correct_index,
        'memory_score':   round(concept_data.get('memory_score', 0.5), 3),
    }


# ─── Result recording ─────────────────────────────────────────────────────────

def record_quiz_result(concept: str, was_correct: bool):
    """
    Feed quiz result into SM-2 scheduling.
    Correct = quality 4 (good recall), wrong = quality 0 (complete miss).
    """
    quality = 4 if was_correct else 0
    try:
        from tracker_app.learning.concept_scheduler import ConceptScheduler
        scheduler = ConceptScheduler()
        scheduler.schedule_next_review(concept, quality=quality)
        logger.info(
            f"Quiz: '{concept}' {'correct' if was_correct else 'wrong'} "
            f"→ quality {quality} fed to SM-2"
        )
    except Exception as e:
        logger.error(f"Failed to record quiz result for '{concept}': {e}")
