"""
Tests: audio classification is honest heuristics, not a synthetic ML stub (C-4).

FKT previously shipped a GaussianNB `audio_classifier.pkl` trained on fully
synthetic random MFCC vectors. That trainer and its loading path were removed;
`classify_audio` must always use the deterministic energy/RMS/ZCR heuristic and
must never consult a model file.

Skipped in CI: audio_module needs sounddevice/librosa, which the reduced Linux
test set does not install.
"""

import numpy as np
import pytest

pytest.importorskip("sounddevice")
pytest.importorskip("librosa")

from tracker_app.tracking import audio_module


def test_silence_classifies_as_silence():
    label, conf = audio_module.classify_audio(np.zeros(22050))
    assert label == "silence"
    assert conf >= 0.9


def test_loud_signal_classifies_within_known_labels():
    rng = np.random.default_rng(0)
    audio = rng.normal(0, 0.2, 22050)
    label, conf = audio_module.classify_audio(audio)
    assert label in {"silence", "speech", "music", "unknown"}
    assert 0.0 <= conf <= 1.0


def test_synthetic_trainer_removed():
    assert not hasattr(audio_module, "train_audio_classifier")
    assert not hasattr(audio_module, "_load_classifier")
    assert not hasattr(audio_module, "_clf_model")


def test_extract_mfcc_features_shape():
    audio = np.random.default_rng(1).normal(0, 0.1, 22050)
    feats = audio_module.extract_mfcc_features(audio)
    assert feats.shape == (39,)
