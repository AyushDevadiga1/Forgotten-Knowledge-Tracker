"""
Tests: intent-feedback toast rate limiting (Phase 10).

The toast must never nag every cycle. /intent/recent only surfaces an
unanswered prediction that has never been shown and is outside the
TOAST_COOLDOWN_MINUTES window; when surfaced, the row is stamped prompted_at.

Run: python -m pytest tracker_app/tests/test_intent_toast_cooldown.py -v
"""

import unittest
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.web.app import app
from tracker_app.db import models
from tracker_app.db.models import Base, IntentPrediction


class ToastCooldownTestBase(unittest.TestCase):
    def setUp(self):
        self.test_engine = create_engine('sqlite:///:memory:')
        self.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.test_engine)

        self.orig_engine = models.engine
        self.orig_session = models.SessionLocal
        models.engine = self.test_engine
        models.SessionLocal = self.TestingSessionLocal

        Base.metadata.create_all(bind=self.test_engine)

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        from tracker_app.tracking import session_state as ss
        self._state_dir = tempfile.mkdtemp()
        self._orig_state_path = ss._STATE_PATH
        ss._STATE_PATH = Path(self._state_dir) / 'session_state.json'

    def tearDown(self):
        from tracker_app.tracking import session_state as ss
        ss._STATE_PATH = self._orig_state_path
        import shutil
        shutil.rmtree(self._state_dir, ignore_errors=True)
        Base.metadata.drop_all(bind=self.test_engine)
        models.engine = self.orig_engine
        models.SessionLocal = self.orig_session

    def _add_prediction(self, **kw):
        with self.TestingSessionLocal() as db:
            row = IntentPrediction(
                predicted_intent=kw.get('predicted_intent', 'studying'),
                confidence=kw.get('confidence', 0.9),
                context_keywords=kw.get('context_keywords', 'a,b'),
                user_feedback=kw.get('user_feedback'),
                actual_intent=kw.get('actual_intent'),
                prompted_at=kw.get('prompted_at'),
            )
            db.add(row)
            db.commit()
            return row.id

    def _get_recent(self):
        resp = self.client.get('/api/v1/intent/recent')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data.get('success'))
        return data.get('data')


class TestToastCooldown(ToastCooldownTestBase):

    def test_empty_db_returns_null(self):
        self.assertIsNone(self._get_recent())

    def test_unanswered_unprompted_prediction_is_surfaced(self):
        self._add_prediction(predicted_intent='studying')
        data = self._get_recent()
        self.assertIsNotNone(data)
        self.assertEqual(data['predicted_intent'], 'studying')

    def test_already_answered_prediction_is_hidden(self):
        self._add_prediction(user_feedback=1)
        self.assertIsNone(self._get_recent())

    def test_already_prompted_prediction_is_hidden(self):
        self._add_prediction(prompted_at=datetime.utcnow())
        self.assertIsNone(self._get_recent())

    def test_surfacing_stamps_prompted_at(self):
        pid = self._add_prediction()
        self.assertIsNotNone(self._get_recent())
        with self.TestingSessionLocal() as db:
            row = db.query(IntentPrediction).filter(IntentPrediction.id == pid).first()
            self.assertIsNotNone(row.prompted_at)

    def test_second_poll_after_surfacing_returns_null(self):
        self._add_prediction()
        self.assertIsNotNone(self._get_recent())
        self.assertIsNone(self._get_recent())

    def test_new_row_within_cooldown_stays_hidden(self):
        self._add_prediction()
        self.assertIsNotNone(self._get_recent())
        self._add_prediction()          # fresh unprompted row
        self.assertIsNone(self._get_recent())   # cooldown still active

    def test_new_row_after_cooldown_is_surfaced(self):
        stale = datetime.utcnow() - timedelta(minutes=6)
        self._add_prediction(prompted_at=stale)
        self._add_prediction(predicted_intent='studying')
        data = self._get_recent()
        self.assertIsNotNone(data)
        self.assertEqual(data['predicted_intent'], 'studying')


if __name__ == '__main__':
    unittest.main()
