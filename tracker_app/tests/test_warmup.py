"""Tests: startup warm-up pre-builds the knowledge graph (Phase 10.5).

warm_up_all_pipelines() pre-loads lazy models in a background thread at startup
so the micro-quiz hot path never triggers a multi-minute SentenceTransformer
embed+sync inside the tracking loop. This verifies the graph is pre-built and
that webcam warm-up only happens when webcam capture is enabled.

psutil/pynput are stubbed globally in conftest.py before any tracker_app
imports, so this fixture only needs to mock the tracker_app-specific modules.

Run: python -m pytest tracker_app/tests/test_warmup.py -v
"""

import sys
import types
import pytest


def _fake_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


@pytest.fixture
def loop_with_fakes(monkeypatch):
    """Import loop.warm_up_all_pipelines with heavy deps faked out."""
    calls = []

    def tracked(name):
        def _inner(*args, **kwargs):
            calls.append(name)
        return _inner

    fakes = {
        "tracker_app.tracking.keyword_extractor": _fake_module(
            "tracker_app.tracking.keyword_extractor",
            get_keyword_extractor=tracked("keyword_extractor")),
        "tracker_app.tracking.intent_module": _fake_module(
            "tracker_app.tracking.intent_module",
            predict_intent=lambda *a, **k: {"intent_label": "studying"},
            _load_model=tracked("intent_module")),
        "tracker_app.tracking.audio_module": _fake_module(
            "tracker_app.tracking.audio_module",
            _load_classifier=tracked("audio_module")),
        "tracker_app.tracking.webcam_module": _fake_module(
            "tracker_app.tracking.webcam_module",
            _get_face_mesh=tracked("webcam_module")),
        "tracker_app.tracking.knowledge_graph": _fake_module(
            "tracker_app.tracking.knowledge_graph",
            get_graph=tracked("knowledge_graph")),
    }

    saved = {}
    for name, mod in fakes.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod

    from tracker_app.tracking import loop
    yield loop, calls

    for name in fakes:
        if saved[name] is not None:
            sys.modules[name] = saved[name]
        else:
            sys.modules.pop(name, None)


def test_warm_up_prebuilds_knowledge_graph(loop_with_fakes):
    """get_graph() is called during warm-up so the hot path stays cached."""
    loop, calls = loop_with_fakes
    loop.warm_up_all_pipelines(webcam_enabled=False)
    assert "knowledge_graph" in calls


def test_warm_up_skips_webcam_when_disabled(loop_with_fakes):
    loop, calls = loop_with_fakes
    loop.warm_up_all_pipelines(webcam_enabled=False)
    assert "webcam_module" not in calls


def test_warm_up_loads_face_mesh_when_webcam_enabled(loop_with_fakes):
    loop, calls = loop_with_fakes
    loop.warm_up_all_pipelines(webcam_enabled=True)
    assert "webcam_module" in calls
    assert "knowledge_graph" in calls


if __name__ == '__main__':
    import sys as _sys
    _sys.exit(pytest.main([__file__, '-v']))