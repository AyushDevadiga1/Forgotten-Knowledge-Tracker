"""Tests for track_loop() and _maybe_trigger_quiz() (F-7).

track_loop() had zero test coverage despite being the most stateful, most
bug-prone code path (bugs H-1 and M-6 slipped through). These tests drive a
full multi-cycle run with mocked pipelines and exercise the quiz trigger:
idle accumulation, the session gate, and the cooldown window.
"""

from datetime import datetime, timedelta

import pytest

import tracker_app.tracking.loop as loop
import tracker_app.web.realtime as realtime
from tracker_app.tracking import quiz_engine


class _FakeCounter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def get_and_reset(self):
        value = self.count
        self.count = 0
        return value


class _FakeMonitor:
    def __init__(self):
        self.is_running = False
        self.starts = 0
        self.keyboard_counter = _FakeCounter()
        self.mouse_counter = _FakeCounter()
        self.concept_calls = []

    def start_session(self):
        self.is_running = True
        self.starts += 1

    def end_session(self):
        self.is_running = False

    def update_attention(self, score):
        pass

    def process_intent(self, result, context=None):
        pass

    def process_concepts(self, keywords, attention_score=0.0):
        self.concept_calls.append(keywords)

    def export_tracking_data(self):
        pass


class _FakeListener:
    def stop(self):
        pass


class _FakeCle:
    def reset(self):
        pass

    def get_cle_score(self):
        return {"cle_score": 0.5}


class _FakeTime:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class _StopAfter:
    def __init__(self, checks):
        self._remaining = checks

    def is_set(self):
        self._remaining -= 1
        return self._remaining <= 0

    def set(self):
        self._remaining = 0


@pytest.fixture(autouse=True)
def _reset_state():
    loop._idle_cycles = 0
    quiz_engine._last_quiz_time = None
    yield
    loop._idle_cycles = 0
    quiz_engine._last_quiz_time = None


@pytest.fixture
def loop_env(monkeypatch):
    monitor = _FakeMonitor()
    ocr_calls = []
    intent_calls = []
    quiz_calls = []

    monkeypatch.setattr(loop, "init_all_databases", lambda: None)
    monkeypatch.setattr(loop, "ActivityMonitor", lambda: monitor)
    monkeypatch.setattr(loop, "get_cle", lambda: _FakeCle())
    monkeypatch.setattr(loop, "start_listeners",
                        lambda m, c: (_FakeListener(), _FakeListener()))
    monkeypatch.setattr(loop, "get_active_window", lambda m: ("notepad", 5.0))
    monkeypatch.setattr(loop, "is_sensitive_window", lambda title: False)
    monkeypatch.setattr(loop, "_get_effective_intervals",
                        lambda: {"ocr": 1, "audio": 1, "webcam": 1})
    monkeypatch.setattr(loop, "_get_attention_score",
                        lambda w, r, c: 60.0)
    monkeypatch.setattr(loop, "session_is_active", lambda: True)
    monkeypatch.setattr(loop, "time", _FakeTime())

    def fake_ocr():
        ocr_calls.append(1)
        return {"keywords": {"hash table": 0.5}}

    monkeypatch.setattr(loop, "get_ocr_pipeline", lambda: fake_ocr)
    monkeypatch.setattr(loop, "get_audio_pipeline", lambda: (
        lambda: None,
        lambda: {"audio_label": "speech", "confidence": 0.9},
    ))
    monkeypatch.setattr(loop, "get_webcam_pipeline", lambda: lambda: {
        "attentiveness_score": 70.0, "face_count": 1,
        "frames_processed": 1, "status": "active",
    })

    def fake_predict(**kw):
        intent_calls.append(kw)
        return {"intent_label": "studying", "confidence": 0.9}

    monkeypatch.setattr(loop, "predict_intent", fake_predict)
    monkeypatch.setattr(loop, "_maybe_trigger_quiz",
                        lambda *a, **k: quiz_calls.append((a, k)))

    return {
        "monitor": monitor, "ocr_calls": ocr_calls,
        "intent_calls": intent_calls, "quiz_calls": quiz_calls,
    }


def test_track_loop_runs_two_cycles_with_mocked_pipelines(loop_env):
    loop.track_loop(stop_event=_StopAfter(3), webcam_enabled=True)

    assert len(loop_env["ocr_calls"]) == 2
    assert len(loop_env["intent_calls"]) == 2
    assert len(loop_env["quiz_calls"]) == 2
    assert loop_env["monitor"].concept_calls, "concepts must be captured each cycle"
    assert loop_env["monitor"].starts == 1
    assert not loop_env["monitor"].is_running, "session must end in finally"


def test_track_loop_resets_state_before_restart(loop_env):
    loop._idle_cycles = 9
    loop.track_loop(stop_event=_StopAfter(2), webcam_enabled=True)
    assert loop._idle_cycles == 0, "H-1: stale idle cycles must not survive a restart"


def test_maybe_trigger_quiz_resets_idle_when_session_inactive(monkeypatch):
    loop._idle_cycles = 7
    monkeypatch.setattr(loop, "session_is_active", lambda: False)
    called = []
    monkeypatch.setattr(quiz_engine, "should_show_quiz",
                        lambda *a, **k: called.append(1) or True)

    loop._maybe_trigger_quiz("idle", False, 0.0)

    assert loop._idle_cycles == 0
    assert called == []


def test_maybe_trigger_quiz_fires_broadcast_and_stamps_cooldown(monkeypatch):
    loop._idle_cycles = 0
    monkeypatch.setattr(loop, "session_is_active", lambda: True)
    monkeypatch.setattr(quiz_engine, "should_show_quiz", lambda *a, **k: True)
    monkeypatch.setattr(quiz_engine, "generate_micro_quiz",
                        lambda graph: {"concept": "hash table"})
    monkeypatch.setattr("tracker_app.tracking.knowledge_graph.get_graph",
                        lambda: object())
    broadcast = []
    monkeypatch.setattr(realtime, "broadcast_micro_quiz",
                        lambda q: broadcast.append(q))
    recorded = []
    monkeypatch.setattr(quiz_engine, "record_quiz_broadcast",
                        lambda: recorded.append(1))

    loop._maybe_trigger_quiz("idle", False, 0.0)

    assert loop._idle_cycles == 1
    assert broadcast == [{"concept": "hash table"}]
    assert recorded == [1], "cooldown must be stamped only after a successful broadcast"


def test_maybe_trigger_quiz_suppressed_inside_cooldown(monkeypatch):
    loop._idle_cycles = 12
    quiz_engine._last_quiz_time = datetime.utcnow() - timedelta(minutes=19)
    monkeypatch.setattr(loop, "session_is_active", lambda: True)
    monkeypatch.setattr(quiz_engine, "generate_micro_quiz",
                        lambda graph: {"concept": "hash table"})
    monkeypatch.setattr("tracker_app.tracking.knowledge_graph.get_graph",
                        lambda: object())
    broadcast = []
    monkeypatch.setattr(realtime, "broadcast_micro_quiz",
                        lambda q: broadcast.append(q))
    injected = quiz_engine._last_quiz_time

    loop._maybe_trigger_quiz("idle", False, 0.0)

    assert loop._idle_cycles == 13
    assert broadcast == []
    assert quiz_engine._last_quiz_time is injected, "failed quiz must not consume cooldown"


def test_maybe_trigger_quiz_fires_once_cooldown_expired(monkeypatch):
    loop._idle_cycles = 12
    quiz_engine._last_quiz_time = datetime.utcnow() - timedelta(minutes=21)
    monkeypatch.setattr(loop, "session_is_active", lambda: True)
    monkeypatch.setattr(quiz_engine, "generate_micro_quiz",
                        lambda graph: {"concept": "hash table"})
    monkeypatch.setattr("tracker_app.tracking.knowledge_graph.get_graph",
                        lambda: object())
    broadcast = []
    monkeypatch.setattr(realtime, "broadcast_micro_quiz",
                        lambda q: broadcast.append(q))

    loop._maybe_trigger_quiz("idle", False, 0.0)

    assert broadcast == [{"concept": "hash table"}]
    assert quiz_engine._last_quiz_time is not None
