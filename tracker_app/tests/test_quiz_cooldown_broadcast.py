"""Tests: quiz cooldown stamped only after a successful broadcast (M-6).

The cooldown used to be consumed when the quiz was *generated*; if the
dashboard broadcast failed, the user never saw the quiz but still paid the
20-minute cooldown. Now generate_micro_quiz() is side-effect free and
loop.py stamps the timer only after broadcast_micro_quiz() succeeds.

Run: python -m pytest tracker_app/tests/test_quiz_cooldown_broadcast.py -v
"""

import networkx as nx
import pytest

from tracker_app.tracking import loop
from tracker_app.tracking import quiz_engine


@pytest.fixture(autouse=True)
def fresh_cooldown(monkeypatch):
    monkeypatch.setattr(quiz_engine, "_last_quiz_time", None)
    monkeypatch.setattr(loop, "_idle_cycles", quiz_engine.IDLE_CYCLES_REQUIRED)


def _graph():
    G = nx.Graph()
    for name, ms in [("alpha", 0.2), ("beta", 0.5), ("gamma", 0.6), ("delta", 0.7)]:
        G.add_node(name, memory_score=ms)
    return G


def test_generate_micro_quiz_has_no_cooldown_side_effect(monkeypatch):
    monkeypatch.setattr(
        quiz_engine,
        "_content_backed_pool",
        lambda: {n: f"{n} is covered in the captured study notes" for n in ["alpha", "beta", "gamma", "delta"]},
    )
    quiz = quiz_engine.generate_micro_quiz(_graph())
    assert quiz is not None
    assert quiz_engine._last_quiz_time is None


def test_record_quiz_broadcast_stamps_cooldown():
    quiz_engine.record_quiz_broadcast()
    assert quiz_engine._last_quiz_time is not None


def test_failed_broadcast_does_not_consume_cooldown(monkeypatch):
    monkeypatch.setattr(loop, "session_is_active", lambda: True)
    monkeypatch.setattr(quiz_engine, "should_show_quiz", lambda *a, **k: True)
    monkeypatch.setattr(quiz_engine, "generate_micro_quiz", lambda graph: {"concept": "x"})
    monkeypatch.setattr(
        "tracker_app.web.realtime.broadcast_micro_quiz",
        lambda quiz: (_ for _ in ()).throw(RuntimeError("dashboard down")),
    )

    loop._maybe_trigger_quiz("idle", False, 50.0)

    assert quiz_engine._last_quiz_time is None


def test_successful_broadcast_stamps_cooldown(monkeypatch):
    monkeypatch.setattr(loop, "session_is_active", lambda: True)
    monkeypatch.setattr(quiz_engine, "should_show_quiz", lambda *a, **k: True)
    monkeypatch.setattr(quiz_engine, "generate_micro_quiz", lambda graph: {"concept": "x"})
    monkeypatch.setattr(
        "tracker_app.web.realtime.broadcast_micro_quiz",
        lambda quiz: None,
    )

    loop._maybe_trigger_quiz("idle", False, 50.0)

    assert quiz_engine._last_quiz_time is not None
