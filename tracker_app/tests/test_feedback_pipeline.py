"""
Tests: ADR-003 feedback-retraining pipeline integrity (Phase 11.1).

The intent classifier is retrained on *real* user corrections, so the stored
feature vector must be the exact 6-element vector used at prediction time —
not the window title. This verifies:
  - predict_intent() returns the features it consumed
  - /intent/feedback round-trips them into FeedbackTrainingSample.feature_vector
  - load_feedback_samples() actually picks corrections back up

Run: python -m pytest tracker_app/tests/test_feedback_pipeline.py -v
"""

import unittest
import json
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tracker_app.web.app import app
from tracker_app.db import models
from tracker_app.db.models import Base, IntentPrediction, FeedbackTrainingSample
from tracker_app.tracking.intent_module import predict_intent

# Module-scope SessionLocal importer (activity_monitor.py does
# `from tracker_app.db.models import SessionLocal`): its captured value is
# whatever is bound at first import, so the harness must rebind it per-test
# (same convention as test_api.py's cs_mod.SessionLocal patch).
from tracker_app.tracking import activity_monitor as am_mod


class FeedbackPipelineBase(unittest.TestCase):
    def setUp(self):
        self.test_engine = create_engine("sqlite:///:memory:")
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)

        self.orig_engine = models.engine
        self.orig_session = models.SessionLocal
        models.engine = self.test_engine
        models.SessionLocal = self.TestingSessionLocal

        self._orig_am_session = am_mod.SessionLocal
        am_mod.SessionLocal = self.TestingSessionLocal

        Base.metadata.create_all(bind=self.test_engine)

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def tearDown(self):
        Base.metadata.drop_all(bind=self.test_engine)
        models.engine = self.orig_engine
        models.SessionLocal = self.orig_session
        am_mod.SessionLocal = self._orig_am_session

    def _add_prediction(self, **kw):
        with self.TestingSessionLocal() as db:
            row = IntentPrediction(
                predicted_intent=kw.get("predicted_intent", "studying"),
                confidence=kw.get("confidence", 0.9),
                context_keywords=kw.get("context_keywords", "[]"),
                window_title=kw.get("window_title"),
            )
            db.add(row)
            db.commit()
            return row.id

    def _submit_feedback(self, prediction_id, actual_intent="idle"):
        return self.client.post(
            "/api/v1/intent/feedback",
            data=json.dumps({"prediction_id": prediction_id, "is_correct": False, "actual_intent": actual_intent}),
            content_type="application/json",
        )


class TestPredictReturnsFeatures(FeedbackPipelineBase):
    def test_predict_intent_includes_6_features(self):
        result = predict_intent(
            {"photosynthesis": {"score": 0.9}, "enzyme": {"score": 0.7}},
            audio_label="silence",
            attention_score=60.0,
            interaction_rate=8.0,
        )
        self.assertIn("features", result)
        self.assertEqual(len(result["features"]), 6)
        self.assertTrue(all(isinstance(f, (int, float)) for f in result["features"]))

    def test_feature_values_match_inputs(self):
        result = predict_intent(
            {"a": 0.9, "b": 0.8},
            audio_label="speech",
            attention_score=75.0,
            interaction_rate=10.0,
            audio_confidence=0.85,
        )
        feats = result["features"]
        # [kw_count, audio_val, attention, interaction, kw_avg_score, audio_conf]
        self.assertEqual(feats[0], 2)
        self.assertEqual(feats[1], 2)  # speech -> 2
        self.assertEqual(feats[2], 75.0)
        self.assertEqual(feats[3], 10.0)
        self.assertAlmostEqual(feats[4], 0.85, places=4)
        self.assertEqual(feats[5], 0.85)


class TestFeedbackRoundTrip(FeedbackPipelineBase):
    def test_correction_stores_real_feature_vector(self):
        feats = json.dumps([3.0, 0.0, 45.0, 2.0, 0.4, 0.7])
        pid = self._add_prediction(context_keywords=feats, window_title="New Tab - Google Chrome")

        resp = self._submit_feedback(pid, actual_intent="idle")
        self.assertEqual(resp.status_code, 200)

        with self.TestingSessionLocal() as db:
            sample = db.query(FeedbackTrainingSample).first()
            self.assertIsNotNone(sample)
            parsed = json.loads(sample.feature_vector)
            self.assertEqual(len(parsed), 6)
            self.assertEqual(parsed, [3.0, 0.0, 45.0, 2.0, 0.4, 0.7])
            self.assertEqual(sample.actual_label, "idle")
            self.assertEqual(sample.window_title, "New Tab - Google Chrome")

    def test_load_feedback_samples_picks_up_correction(self):
        from tracker_app.scripts.train_models_from_logs import load_feedback_samples

        feats = json.dumps([6.0, 2.0, 70.0, 12.0, 0.7, 0.9])
        pid = self._add_prediction(
            context_keywords=feats, predicted_intent="studying", window_title="FKT - Antigravity IDE"
        )

        self._submit_feedback(pid, actual_intent="studying")

        X_fb, y_fb = load_feedback_samples()
        self.assertEqual(len(X_fb), 1)
        self.assertEqual(X_fb[0], [6.0, 2.0, 70.0, 12.0, 0.7, 0.9])
        self.assertEqual(y_fb[0], "studying")

    def test_legacy_window_title_vector_is_skipped_gracefully(self):
        # Old rows stored the window title in context_keywords (not JSON).
        from tracker_app.scripts.train_models_from_logs import load_feedback_samples

        pid = self._add_prediction(context_keywords="New Tab - Google Chrome", window_title=None)

        self._submit_feedback(pid, actual_intent="idle")

        X_fb, y_fb = load_feedback_samples()
        self.assertEqual(len(X_fb), 0)
        self.assertEqual(len(y_fb), 0)


class TestFeatureVectorJsonContract(FeedbackPipelineBase):
    """FKT-F-005: context_keywords / feature_vector must always be valid JSON.

    The producer must never store a raw window title in the JSON-documented
    context_keywords column, and the bridge must never forward malformed
    values into the training pipeline.
    """

    def test_log_prediction_without_features_stores_empty_vector_json(self):
        from tracker_app.tracking.activity_monitor import IntentValidator

        validator = IntentValidator()
        validator.log_prediction("idle", 0.5, context="Some Window Title", features=None)

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).first()
            self.assertIsNotNone(pred)
            self.assertEqual(pred.context_keywords, "[]")  # valid JSON, not a title
            self.assertEqual(json.loads(pred.context_keywords), [])
            # The title is kept in its own column, not the JSON one.
            self.assertEqual(pred.window_title, "Some Window Title")

    def test_feedback_on_non_json_vector_records_correction_but_no_sample(self):
        # Legacy rows stored the window title in context_keywords (not JSON).
        pid = self._add_prediction(
            context_keywords="FKT - Antigravity IDE", predicted_intent="idle", window_title="FKT - Antigravity IDE"
        )

        resp = self._submit_feedback(pid, actual_intent="Coding")
        self.assertEqual(resp.status_code, 200)

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).filter(IntentPrediction.id == pid).first()
            self.assertEqual(pred.user_feedback, 0)  # feedback still recorded
            self.assertEqual(pred.actual_intent, "Coding")
            self.assertIsNotNone(pred.feedback_timestamp)
            self.assertIsNone(db.query(FeedbackTrainingSample).first())  # no garbage sample

    def test_feedback_on_json_non_list_vector_skips_sample(self):
        # JSON that parses but is not a list (live DB had scalar '3') must not
        # create a training sample either.
        from tracker_app.web.api import FeedbackService

        pid = self._add_prediction(context_keywords="3", predicted_intent="idle")

        FeedbackService.record_feedback(pid, is_correct=False, actual_intent="Coding")

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).filter(IntentPrediction.id == pid).first()
            self.assertEqual(pred.user_feedback, 0)
            self.assertIsNone(db.query(FeedbackTrainingSample).first())

    def test_feedback_on_wrong_length_vector_skips_sample(self):
        # '[]' parses as JSON but is not a 6-element vector — no sample.
        from tracker_app.web.api import FeedbackService

        pid = self._add_prediction(context_keywords="[]", predicted_intent="idle")

        FeedbackService.record_feedback(pid, is_correct=False, actual_intent="Coding")

        with self.TestingSessionLocal() as db:
            self.assertIsNone(db.query(FeedbackTrainingSample).first())

    def test_log_prediction_with_features_round_trips_to_training_sample(self):
        # Positive control: a real 6-vector from the producer still flows into
        # a training sample through the bridge.
        from tracker_app.tracking.activity_monitor import IntentValidator
        from tracker_app.web.api import FeedbackService

        feats = [3.0, 0.0, 45.0, 2.0, 0.4, 0.7]
        validator = IntentValidator()
        validator.log_prediction("studying", 0.9, context="FKT - Antigravity IDE", features=feats)

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).first()
            self.assertIsNotNone(pred)
            self.assertEqual(json.loads(pred.context_keywords), feats)
            pid = pred.id

        FeedbackService.record_feedback(pid, is_correct=False, actual_intent="studying")

        with self.TestingSessionLocal() as db:
            sample = db.query(FeedbackTrainingSample).first()
            self.assertIsNotNone(sample)
            self.assertEqual(json.loads(sample.feature_vector), feats)
            self.assertEqual(sample.actual_label, "studying")
            self.assertEqual(sample.window_title, "FKT - Antigravity IDE")


class TestStrictBooleanFeedback(FeedbackPipelineBase):
    """The API must not treat the string "false" as True.

    bool("false") is True, so the old `bool(data['is_correct'])` silently
    recorded a *correct* answer for a JSON string "false" — the correction was
    dropped and the accuracy stats counted a wrong answer as right.
    """

    def test_string_false_is_treated_as_false(self):
        # Sample creation requires a valid 6-element feature vector (FKT-F-005),
        # so the fixture carries one instead of the old '[]' placeholder.
        pid = self._add_prediction(context_keywords=json.dumps([2.0, 1.0, 60.0, 8.0, 0.6, 0.5]))
        resp = self.client.post(
            "/api/v1/intent/feedback",
            data=json.dumps({"prediction_id": pid, "is_correct": "false", "actual_intent": "idle"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).filter(IntentPrediction.id == pid).first()
            self.assertEqual(pred.user_feedback, 0)  # incorrect, not correct
            sample = db.query(FeedbackTrainingSample).first()
            self.assertIsNotNone(sample)  # correction WAS stored
            self.assertEqual(sample.actual_label, "idle")

    def test_string_true_is_treated_as_true(self):
        pid = self._add_prediction(context_keywords="[]")
        resp = self.client.post(
            "/api/v1/intent/feedback",
            data=json.dumps({"prediction_id": pid, "is_correct": "true"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).filter(IntentPrediction.id == pid).first()
            self.assertEqual(pred.user_feedback, 1)
            self.assertIsNone(db.query(FeedbackTrainingSample).first())

    def test_non_boolean_value_rejected_with_400(self):
        pid = self._add_prediction(context_keywords="[]")
        resp = self.client.post(
            "/api/v1/intent/feedback",
            data=json.dumps({"prediction_id": pid, "is_correct": "maybe", "actual_intent": "idle"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        with self.TestingSessionLocal() as db:
            pred = db.query(IntentPrediction).filter(IntentPrediction.id == pid).first()
            self.assertIsNone(pred.user_feedback)  # nothing recorded

    def test_string_false_still_requires_actual_intent(self):
        """The 'false requires actual_intent' validation must see the parsed
        value — the old `not data['is_correct']` check never fired for the
        string "false" (not "false" == False)."""
        pid = self._add_prediction(context_keywords="[]")
        resp = self.client.post(
            "/api/v1/intent/feedback",
            data=json.dumps({"prediction_id": pid, "is_correct": "false"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
