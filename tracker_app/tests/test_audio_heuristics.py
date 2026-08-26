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


# ─── Feature-driven labels (replaces the three-threshold version) ────────────


def _make(fn):
    sr = audio_module.SAMPLE_RATE
    dur = 4.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    rng = np.random.default_rng(0)
    return fn(t, rng, sr, dur)


def _tone(t, rng, sr, dur):
    return 0.25 * np.sin(2 * np.pi * 440 * t)


def _white_noise(t, rng, sr, dur):
    return 0.2 * rng.standard_normal(int(sr * dur))


def _speech_am(t, rng, sr, dur):
    return 0.25 * (0.6 + 0.4 * np.sin(2 * np.pi * 5 * t)) * rng.standard_normal(int(sr * dur))


def _music_slowam(t, rng, sr, dur):
    # Noise-like music modulated below the syllabic band (0.7 Hz).
    return 0.25 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t)) * rng.standard_normal(int(sr * dur))


def test_tonal_signal_is_music():
    label, _conf = audio_module.classify_audio(_make(_tone))
    assert label == "music"


def test_steady_broadband_is_not_speech():
    # The old classifier called white noise 'speech' (high ZCR + bright
    # centroid). Without syllabic-rate modulation it must be unknown/music.
    label, _ = audio_module.classify_audio(_make(_white_noise))
    assert label != "speech"


def test_syllabic_modulation_is_speech():
    label, _conf = audio_module.classify_audio(_make(_speech_am))
    assert label == "speech"


def test_sub_syllabic_modulation_is_not_speech():
    label, _ = audio_module.classify_audio(_make(_music_slowam))
    assert label != "speech"


def test_syllabic_modulation_feature_is_zero_for_silence():
    assert audio_module._syllabic_modulation(np.zeros(22050)) == 0.0
