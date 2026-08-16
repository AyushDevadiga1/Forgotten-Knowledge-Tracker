"""Regression tests for L-4: webcam_pipeline returns the true face count.

The old code returned `1 if ear_values else 0` ? a boolean cast, so a frame
with multiple detected faces still reported 1. The pipeline now counts the
faces per frame and reports the maximum seen across frames.
"""

import pytest

import tracker_app.tracking.webcam_module as wm


class _Face:
    def __init__(self, landmark):
        self.landmark = landmark


class _Results:
    def __init__(self, faces):
        self.multi_face_landmarks = faces


class _FakeFaceMesh:
    def __init__(self, per_frame):
        self._per_frame = per_frame
        self.used = 0

    def process(self, rgb_frame):
        out = self._per_frame[self.used]
        self.used += 1
        return out


def _run(num_faces_per_frame, monkeypatch):
    frames = [_Results([_Face(None)] * n) for n in num_faces_per_frame]
    fake = _FakeFaceMesh(frames)
    monkeypatch.setattr(wm.cv2, "cvtColor", lambda f, c: f)
    monkeypatch.setattr(wm, "eye_aspect_ratio", lambda lm, idx: 0.3)
    monkeypatch.setattr(wm, "_get_face_mesh", lambda: fake)
    monkeypatch.setattr(wm, "capture_frame", lambda: object())
    monkeypatch.setattr(wm.time, "sleep", lambda s: None)
    return wm.webcam_pipeline(num_frames=len(frames))


def test_face_count_reports_true_number(monkeypatch):
    result = _run([2, 1], monkeypatch)
    assert result["face_count"] == 2
    assert result["status"] == "active"
    assert isinstance(result["attentiveness_score"], float)


def test_face_count_is_max_not_sum(monkeypatch):
    result = _run([2, 3], monkeypatch)
    assert result["face_count"] == 3


def test_face_count_zero_when_no_faces(monkeypatch):
    result = _run([0, 0], monkeypatch)
    assert result["face_count"] == 0
    assert result["status"] == "no_face_detected"


def test_face_count_zero_when_mediapipe_unavailable(monkeypatch):
    monkeypatch.setattr(wm, "_get_face_mesh", lambda: None)
    result = wm.webcam_pipeline(num_frames=3)
    assert result["face_count"] == 0
    assert result["status"] == "mediapipe_unavailable"
    assert result["frames_processed"] == 0
