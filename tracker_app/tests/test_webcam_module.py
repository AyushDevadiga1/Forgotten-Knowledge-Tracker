"""Tests: persistent webcam capture handle.

The camera used to be opened and closed on every capture_frame() call, so a
3-frame webcam cycle did 3 open/close cycles (~300 ms each) and toggled the
camera LED on every run. The handle is now opened once and reused; it is
released on read failure (so a dropped camera can re-open) and on shutdown.
"""

import pytest

import tracker_app.tracking.webcam_module as wm


class _FakeCap:
    def __init__(self, frame=None, is_opened=True):
        self._frame = frame
        self._opened = is_opened
        self.read_calls = 0
        self.release_calls = 0

    def isOpened(self):
        return self._opened

    def set(self, *args):
        return True

    def read(self):
        self.read_calls += 1
        return (True, self._frame)

    def release(self):
        self.release_calls += 1
        self._opened = False


@pytest.fixture(autouse=True)
def _reset_cap():
    wm._cap = None
    yield
    wm._cap = None


def test_capture_reuses_single_handle(monkeypatch):
    frame = object()
    cap = _FakeCap(frame=frame)
    opens = {"n": 0}

    def fake_videocapture(index):
        opens["n"] += 1
        assert index == 0
        return cap

    monkeypatch.setattr(wm.cv2, "VideoCapture", fake_videocapture)

    f1 = wm.capture_frame()
    f2 = wm.capture_frame()
    f3 = wm.capture_frame()

    assert f1 is frame and f2 is frame and f3 is frame
    assert opens["n"] == 1  # opened once, not once per frame
    assert wm._cap is cap
    assert cap.read_calls == 3
    assert cap.release_calls == 0  # not released between frames
    wm._release_cap()
    assert cap.release_calls == 1
    assert wm._cap is None


def test_failed_open_returns_none(monkeypatch):
    cap = _FakeCap(is_opened=False)
    monkeypatch.setattr(wm.cv2, "VideoCapture", lambda index: cap)

    assert wm.capture_frame() is None
    assert wm._cap is None  # no dead handle held
    assert cap.release_calls == 1


def test_read_failure_releases_and_recovers(monkeypatch):
    frame = object()
    cap1 = _FakeCap(frame=None)  # read returns (True, None)
    cap2 = _FakeCap(frame=frame)
    caps = [cap1, cap2]
    opens = {"n": 0}

    def fake_videocapture(index):
        c = caps[opens["n"]]
        opens["n"] += 1
        return c

    monkeypatch.setattr(wm.cv2, "VideoCapture", fake_videocapture)

    assert wm.capture_frame() is None
    assert wm._cap is None
    assert cap1.release_calls == 1

    assert wm.capture_frame() is frame  # fresh handle is acquired
    assert opens["n"] == 2
    assert wm._cap is cap2
    wm._release_cap()
    assert cap2.release_calls == 1


def test_runtime_code_uses_logger_not_print():
    import inspect

    src = inspect.getsource(wm)
    main_idx = src.find('if __name__ == "__main__":')
    body = src if main_idx == -1 else src[:main_idx]
    assert "print(" not in body  # Runtime messages must reach the log
