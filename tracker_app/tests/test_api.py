"""
Unit Tests: Flask API Endpoints
================================
Tests all API routes using Flask's test client with isolated in-memory DB.
Run: python -m pytest tracker_app/tests/test_api.py -v
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
from tracker_app.db.models import Base
import tracker_app.learning.concept_scheduler as cs_mod


class TestAPIBase(unittest.TestCase):
    def setUp(self):
        # Override SQLAlchemy to use in-memory db for testing
        self.test_engine = create_engine("sqlite:///:memory:")
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)

        # Patch the models module being used by the app and api
        self.orig_engine = models.engine
        self.orig_session = models.SessionLocal
        models.engine = self.test_engine
        models.SessionLocal = self.TestingSessionLocal

        # ConceptScheduler captures SessionLocal at import time (db/models import
        # in concept_scheduler.py), so it must be re-bound here too or ingest
        # writes leak into the real data/sessions.db (this breaks once the real
        # DB lags the ORM schema, e.g. migration 010's review_count).
        self._orig_cs_session = cs_mod.SessionLocal
        cs_mod.SessionLocal = self.TestingSessionLocal

        Base.metadata.create_all(bind=self.test_engine)

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for tests
        self.client = app.test_client()


    def tearDown(self):
        Base.metadata.drop_all(bind=self.test_engine)
        models.engine = self.orig_engine
        models.SessionLocal = self.orig_session
        cs_mod.SessionLocal = self._orig_cs_session


class TestAPIGetItems(TestAPIBase):
    def test_get_items_returns_200(self):
        resp = self.client.get("/api/v1/items")
        self.assertEqual(resp.status_code, 200)

    def test_get_items_response_shape(self):
        resp = self.client.get("/api/v1/items")
        data = json.loads(resp.data)
        self.assertIn("success", data)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_get_items_empty_db_returns_empty_list(self):
        resp = self.client.get("/api/v1/items")
        data = json.loads(resp.data)
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["data"], [])


class TestAPICreateItem(TestAPIBase):
    def test_create_valid_item_returns_201(self):
        resp = self.client.post(
            "/api/v1/items",
            data=json.dumps({"question": "What is Python?", "answer": "A language."}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_create_item_returns_id(self):
        resp = self.client.post(
            "/api/v1/items", data=json.dumps({"question": "Q?", "answer": "A."}), content_type="application/json"
        )
        data = json.loads(resp.data)
        self.assertIn("data", data)
        self.assertIn("id", data["data"])

    def test_create_item_then_retrieve(self):
        self.client.post(
            "/api/v1/items",
            data=json.dumps({"question": "What is a decorator?", "answer": "A wrapper."}),
            content_type="application/json",
        )
        resp = self.client.get("/api/v1/items")
        data = json.loads(resp.data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["data"][0]["question"], "What is a decorator?")

    def test_create_item_numeric_fields_are_coerced_not_crashed(self):
        """Sibling of the record_review crash: `int.strip()` on a JSON number
        raised AttributeError before the try block -> unhandled 500."""
        resp = self.client.post(
            "/api/v1/items", data=json.dumps({"question": 12345, "answer": 67890}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)

        item_id = json.loads(resp.data)["data"]["id"]
        resp = self.client.get(f"/api/v1/items/{item_id}")
        data = json.loads(resp.data)["data"]
        self.assertEqual(data["question"], "12345")
        self.assertEqual(data["answer"], "67890")

    def test_create_item_null_question_still_requires_field(self):
        resp = self.client.post(
            "/api/v1/items", data=json.dumps({"question": None, "answer": "A."}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)


class TestAPIBrowserIngest(TestAPIBase):
    def test_ingest_saves_concepts(self):
        resp = self.client.post(
            "/api/v1/ingest",
            data=json.dumps(
                {
                    "text": (
                        "The mitochondria is the powerhouse of the cell. "
                        "Cellular respiration converts glucose into ATP "
                        "through the Krebs cycle and oxidative phosphorylation. "
                        "This process produces the energy currency of the cell."
                    ),
                    "title": "Biology notes",
                }
            ),
            content_type="application/json",
        )
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["success"])
        self.assertGreater(data["concepts_saved"], 0)
        self.assertIn("keywords", data)

    def test_ingest_rejects_short_text(self):
        resp = self.client.post(
            "/api/v1/ingest", data=json.dumps({"text": "hi", "title": "x"}), content_type="application/json"
        )
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIn("skipped", data["message"])

    def test_ingest_requires_text_field(self):
        resp = self.client.post("/api/v1/ingest", data=json.dumps({"title": "x"}), content_type="application/json")
        self.assertEqual(resp.status_code, 400)


class TestAPIRecordReview(TestAPIBase):
    def test_record_review_valid(self):
        resp = self.client.post(
            "/api/v1/items", data=json.dumps({"question": "Q?", "answer": "A."}), content_type="application/json"
        )
        item_id = json.loads(resp.data)["data"]["id"]

        resp = self.client.post(
            "/api/v1/reviews", data=json.dumps({"item_id": item_id, "quality": 4}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_record_review_numeric_item_id_is_400_not_500(self):
        """A JSON-number item_id (e.g. a JS client serialising an id number)
        must not crash the route — previously `int.strip()` raised
        AttributeError outside the try block and the request died as a 500.
        The unknown item is then a normal 400 'not found' contract error."""
        resp = self.client.post(
            "/api/v1/reviews", data=json.dumps({"item_id": 424242, "quality": 4}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(json.loads(resp.data)["success"])

    def test_record_review_null_item_id_is_400(self):
        resp = self.client.post(
            "/api/v1/reviews", data=json.dumps({"item_id": None, "quality": 4}), content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)


class TestAPISessions(TestAPIBase):
    """Phase 9: study-session toggle endpoints."""

    def test_status_defaults_inactive(self):
        resp = self.client.get("/api/v1/session/status")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIs(data["data"]["active"], False)

    def test_start_activates_session(self):
        resp = self.client.post("/api/v1/session/start")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIs(data["data"]["active"], True)

        status = json.loads(self.client.get("/api/v1/session/status").data)
        self.assertIs(status["data"]["active"], True)

    def test_stop_deactivates_session(self):
        self.client.post("/api/v1/session/start")
        resp = self.client.post("/api/v1/session/stop")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIs(data["data"]["active"], False)

    def test_start_stop_are_idempotent(self):
        self.client.post("/api/v1/session/start")
        data = json.loads(self.client.post("/api/v1/session/start").data)
        self.assertIs(data["data"]["active"], True)

        self.client.post("/api/v1/session/stop")
        data = json.loads(self.client.post("/api/v1/session/stop").data)
        self.assertIs(data["data"]["active"], False)

    def test_status_reports_elapsed_while_active(self):
        self.client.post("/api/v1/session/start")
        status = json.loads(self.client.get("/api/v1/session/status").data)
        self.assertGreaterEqual(status["data"]["elapsed_seconds"], 0)


class TestAPIStatsTrend(TestAPIBase):
    """Real per-day time-series backing the Overview sparklines (H-2)."""

    def test_trend_defaults_to_7_day_buckets(self):
        resp = self.client.get("/api/v1/stats/trend")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 7)
        self.assertEqual(
            set(data["data"][0].keys()), {"date", "reviews", "correct", "added", "mastered", "due", "accuracy"}
        )

    def test_trend_empty_db_is_all_zeros(self):
        data = json.loads(self.client.get("/api/v1/stats/trend?days=3").data)
        self.assertEqual(len(data["data"]), 3)
        for day in data["data"]:
            self.assertEqual(day["reviews"], 0)
            self.assertEqual(day["added"], 0)
            self.assertEqual(day["mastered"], 0)
            self.assertEqual(day["due"], 0)
            self.assertEqual(day["accuracy"], 0)

    def test_trend_reflects_real_reviews_and_additions(self):
        resp = self.client.post(
            "/api/v1/items",
            data=json.dumps({"question": "What is ATP?", "answer": "Energy currency."}),
            content_type="application/json",
        )
        item_id = json.loads(resp.data)["data"]["id"]

        self.client.post(
            "/api/v1/reviews", data=json.dumps({"item_id": item_id, "quality": 5}), content_type="application/json"
        )

        trend = json.loads(self.client.get("/api/v1/stats/trend?days=1").data)["data"]
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["added"], 1)
        self.assertEqual(trend[0]["reviews"], 1)
        self.assertEqual(trend[0]["correct"], 1)
        self.assertEqual(trend[0]["accuracy"], 100)

    def test_trend_rejects_invalid_days(self):
        self.assertEqual(self.client.get("/api/v1/stats/trend?days=0").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/stats/trend?days=abc").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/stats/trend?days=1000").status_code, 400)


class TestDailySummaryRange(TestAPIBase):
    """M-4: date filter must be a range, not a string LIKE."""

    def test_daily_summary_uses_range_boundaries(self):
        from datetime import datetime, timedelta
        from tracker_app.db.models import TrackingSession
        from tracker_app.db.repository import TrackingRepository

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_evening = today_start - timedelta(seconds=1)
        tomorrow_morning = today_start + timedelta(days=1, seconds=1)

        with self.TestingSessionLocal() as db:
            for label, ts, minutes in (
                ("inside-1", today_start, 30.0),
                ("inside-2", today_start + timedelta(hours=12), 20.0),
                ("yesterday", yesterday_evening, 90.0),
                ("tomorrow", tomorrow_morning, 60.0),
            ):
                db.add(
                    TrackingSession(start_time=ts, duration_minutes=minutes, concepts_encountered=1, avg_attention=0.5)
                )
            db.commit()

            summary = TrackingRepository.get_daily_summary(db, date=now)
        self.assertEqual(summary["date"], now.strftime("%Y-%m-%d"))
        self.assertAlmostEqual(summary["total_minutes"], 50.0)
        self.assertEqual(summary["concepts"], 2)

    def test_daily_summary_empty_day_is_zero(self):
        from datetime import datetime, timedelta
        from tracker_app.db.models import TrackingSession
        from tracker_app.db.repository import TrackingRepository

        old = datetime.utcnow() - timedelta(days=30)
        with self.TestingSessionLocal() as db:
            db.add(TrackingSession(start_time=old, duration_minutes=99.0, concepts_encountered=9, avg_attention=0.9))
            db.commit()
            summary = TrackingRepository.get_daily_summary(db, date=datetime.utcnow())
        self.assertEqual(summary["total_minutes"], 0)
        self.assertEqual(summary["concepts"], 0)


class TestTrendAnalysisBoundary(TestAPIBase):
    """get_trend_analysis must include every session on the boundary day that
    started after the cutoff time-of-day.

    Regression: the cutoff was passed to SQLAlchemy as an isoformat() string
    ("2026-08-04T12:00:00") while SQLite stores DateTime as
    "2026-08-04 15:00:00" — lexicographically, space < 'T', so same-day
    sessions after the cutoff time were silently excluded from the trend.
    """

    def test_boundary_day_sessions_after_cutoff_are_included(self):
        from datetime import datetime, timedelta
        from unittest import mock
        from tracker_app.db.models import TrackingSession
        from tracker_app.db.repository import TrackingRepository

        fixed_now = datetime(2026, 8, 11, 12, 0, 0)  # midday → wide same-day window
        cutoff = fixed_now - timedelta(days=7)  # 2026-08-04 12:00

        with self.TestingSessionLocal() as db:
            for label, ts in (
                ("after-cutoff", cutoff + timedelta(hours=3)),  # same day, include
                ("before-cutoff", cutoff - timedelta(hours=7)),  # same day, exclude
                ("next-day", cutoff + timedelta(days=1)),  # include
                ("stale", cutoff - timedelta(days=10)),  # exclude
            ):
                db.add(TrackingSession(start_time=ts, duration_minutes=10.0, concepts_encountered=1, avg_attention=0.5))
            db.commit()

            with mock.patch("tracker_app.db.repository._utcnow", return_value=fixed_now):
                result = TrackingRepository.get_trend_analysis(db, days=7)

        self.assertEqual(result["tracking_days"], 2)


class TestAPIQuizAnswerStrictBoolean(TestAPIBase):
    """/quiz/answer must not treat the string "false" as True.

    Regression: `bool(data['was_correct'])` recorded a *correct* SM-2 result
    for "false", so a wrong answer was scheduled as a successful recall.
    """

    def _add_concept(self, concept="quiz-probe"):
        from tracker_app.db.models import TrackedConcept

        with self.TestingSessionLocal() as db:
            db.add(TrackedConcept(concept=concept))
            db.commit()

    def test_string_false_records_wrong_answer(self):
        from tracker_app.db.models import TrackedConcept

        self._add_concept()

        resp = self.client.post(
            "/api/v1/quiz/answer",
            data=json.dumps({"concept": "quiz-probe", "was_correct": "false"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        with self.TestingSessionLocal() as db:
            row = db.query(TrackedConcept).filter(TrackedConcept.concept == "quiz-probe").first()
            # quality 0 → ease drops to 1.7 (2.5 + 0.1 - 5*(0.08 + 5*0.02)).
            # A "false" recorded as correct would leave ease at 2.5.
            self.assertAlmostEqual(row.memory_strength, 1.7, places=4)
            self.assertEqual(row.repetitions, 1)

    def test_invalid_was_correct_rejected_with_400(self):
        self._add_concept()
        resp = self.client.post(
            "/api/v1/quiz/answer",
            data=json.dumps({"concept": "quiz-probe", "was_correct": "maybe"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestAPIInputValidationNoCrash(TestAPIBase):
    """Runtime-monitoring regression (FKT-R-001/002/003/004): malformed JSON
    bodies, non-object JSON bodies, bad enums, and non-integer query params
    must return 400 -- never an unhandled 500.

    Before the fix: data.get / 'x' in data on a JSON string/array crashed
    with AttributeError/TypeError, LearningItemType('nope') raised inside the
    try block, and int('abc') fell into the catch-all -> 500.
    """

    def _post_raw_json(self, path, raw):
        return self.client.post(path, data=raw, content_type="application/json")

    def test_items_string_body_is_400(self):
        resp = self._post_raw_json("/api/v1/items", '"solo string"')
        self.assertEqual(resp.status_code, 400)

    def test_items_array_body_is_400(self):
        resp = self._post_raw_json("/api/v1/items", "[1,2,3]")
        self.assertEqual(resp.status_code, 400)

    def test_reviews_string_body_is_400(self):
        resp = self._post_raw_json("/api/v1/reviews", '"solo string"')
        self.assertEqual(resp.status_code, 400)

    def test_quiz_answer_number_body_is_400(self):
        resp = self._post_raw_json("/api/v1/quiz/answer", "123")
        self.assertEqual(resp.status_code, 400)

    def test_ingest_number_body_is_400(self):
        resp = self._post_raw_json("/api/v1/ingest", "123")
        self.assertEqual(resp.status_code, 400)

    def test_intent_feedback_number_body_is_400(self):
        resp = self._post_raw_json("/api/v1/intent/feedback", "123")
        self.assertEqual(resp.status_code, 400)

    def test_items_invalid_item_type_is_400(self):
        resp = self._post_raw_json("/api/v1/items", '{"question": "q", "answer": "a", "item_type": "nope"}')
        self.assertEqual(resp.status_code, 400)
        self.assertIn("item_type", json.loads(resp.data)["error"])

    def test_intent_feedback_noninteger_prediction_id_is_400(self):
        resp = self._post_raw_json("/api/v1/intent/feedback", '{"prediction_id": "abc", "is_correct": true}')
        self.assertEqual(resp.status_code, 400)

    def test_graph_gaps_noninteger_limit_is_400(self):
        resp = self.client.get("/api/v1/graph/gaps?limit=abc")
        self.assertEqual(resp.status_code, 400)

    def test_graph_gaps_out_of_range_limit_is_400(self):
        resp = self.client.get("/api/v1/graph/gaps?limit=999")
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
