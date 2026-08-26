# -*- coding: ascii -*-
"""F-4 regression tests: FeedbackTrainingSample.used_in_training lifecycle.

Samples consumed by a retraining run must be marked used_in_training=1, and
the periodic cleanup must delete only used rows older than the retention
window so the table cannot grow without bound.
"""

import datetime
import json
import sqlite3
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.db import models
from tracker_app.db import repository as repo_mod
from tracker_app.db.migrations import run_migrations
from tracker_app.db.models import Base, FeedbackTrainingSample


class FeedbackUsedBase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.orig_engine = models.engine
        self.orig_session = models.SessionLocal
        models.engine = self.engine
        models.SessionLocal = self.Session
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        models.engine = self.orig_engine
        models.SessionLocal = self.orig_session

    def _add_sample(self, ts, used=False):
        with self.Session() as db:
            s = FeedbackTrainingSample(
                timestamp=ts,
                feature_vector=json.dumps([1.0] * 6),
                predicted_label="idle",
                actual_label="studying",
                used_in_training=1 if used else 0,
            )
            db.add(s)
            db.commit()
            return s.id


class TestUsedInTrainingFlag(FeedbackUsedBase):
    def test_new_sample_defaults_to_unused(self):
        with self.Session() as db:
            s = FeedbackTrainingSample(
                timestamp=datetime.datetime.utcnow(),
                feature_vector="[]",
                predicted_label="a",
                actual_label="b",
            )
            db.add(s)
            db.commit()
            self.assertEqual(s.used_in_training, 0)

    def test_mark_samples_used(self):
        sid = self._add_sample(datetime.datetime.utcnow())
        with self.Session() as db:
            repo_mod.FeedbackRepository.mark_samples_used(db, [sid])
        with self.Session() as db:
            self.assertEqual(db.get(FeedbackTrainingSample, sid).used_in_training, 1)

    def test_mark_samples_used_empty_is_noop(self):
        with self.Session() as db:
            repo_mod.FeedbackRepository.mark_samples_used(db, [])

    def test_cleanup_deletes_only_used_and_old(self):
        now = datetime.datetime.utcnow()
        old_used = self._add_sample(now - datetime.timedelta(days=200), used=True)
        old_unused = self._add_sample(now - datetime.timedelta(days=200), used=False)
        new_used = self._add_sample(now - datetime.timedelta(days=1), used=True)
        with self.Session() as db:
            deleted = repo_mod.FeedbackRepository.cleanup_used_samples(db, now - datetime.timedelta(days=90))
        self.assertEqual(deleted, 1)
        with self.Session() as db:
            self.assertIsNone(db.get(FeedbackTrainingSample, old_used))
            self.assertIsNotNone(db.get(FeedbackTrainingSample, old_unused))
            self.assertIsNotNone(db.get(FeedbackTrainingSample, new_used))


class TestTrainerMarkAndCleanup(FeedbackUsedBase):
    def test_load_feedback_samples_marks_used_and_prunes_old(self):
        from tracker_app.scripts.train_models_from_logs import load_feedback_samples

        now = datetime.datetime.utcnow()
        old_used = self._add_sample(now - datetime.timedelta(days=200), used=True)
        fresh = self._add_sample(now, used=False)

        # The 200-day-old used sample is still valid training data, so it
        # loads here too; the run then marks the fresh one used and prunes
        # the old used row.
        X, y = load_feedback_samples()

        self.assertEqual(len(X), 2)
        self.assertEqual(y, ["studying", "studying"])
        with self.Session() as db:
            self.assertEqual(db.get(FeedbackTrainingSample, fresh).used_in_training, 1)
            self.assertIsNone(db.get(FeedbackTrainingSample, old_used))

    def test_load_feedback_samples_leaves_recent_used_samples(self):
        from tracker_app.scripts.train_models_from_logs import load_feedback_samples

        now = datetime.datetime.utcnow()
        recent_used = self._add_sample(now - datetime.timedelta(days=10), used=True)

        X, _ = load_feedback_samples()

        self.assertEqual(len(X), 1)
        with self.Session() as db:
            self.assertIsNotNone(db.get(FeedbackTrainingSample, recent_used))
            self.assertEqual(db.get(FeedbackTrainingSample, recent_used).used_in_training, 1)


def test_migration_013_adds_column_to_stale_table(tmp_path):
    """A pre-013 feedback_training_samples table gains used_in_training."""
    db_file = str(tmp_path / "stale_feedback.db")
    conn = sqlite3.connect(db_file)
    try:
        conn.execute("""
            CREATE TABLE feedback_training_samples (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                feature_vector  TEXT    NOT NULL,
                predicted_label TEXT    NOT NULL,
                actual_label    TEXT    NOT NULL,
                confidence      REAL    DEFAULT 0.0,
                window_title    TEXT    DEFAULT ''
            )
        """)
        conn.commit()
    finally:
        conn.close()

    result = run_migrations(db_path=db_file)
    assert result["failed"] == 0, result["errors"]

    conn = sqlite3.connect(db_file)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(feedback_training_samples)")]
        assert "used_in_training" in cols
        conn.execute("""
            INSERT INTO feedback_training_samples
            (timestamp, feature_vector, predicted_label, actual_label)
            VALUES ('2026-01-01 00:00:00', '[]', 'idle', 'studying')
        """)
        row = conn.execute("SELECT used_in_training FROM feedback_training_samples").fetchone()
        assert row[0] == 0
    finally:
        conn.close()
