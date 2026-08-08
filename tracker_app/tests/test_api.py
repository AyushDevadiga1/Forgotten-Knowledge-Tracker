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
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.web.app import app
from tracker_app.db import models
from tracker_app.db.models import Base, IntentPrediction
import tracker_app.learning.concept_scheduler as cs_mod

class TestAPIBase(unittest.TestCase):
    def setUp(self):
        # Override SQLAlchemy to use in-memory db for testing
        self.test_engine = create_engine('sqlite:///:memory:')
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

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
        self.client = app.test_client()

        # Isolate the shared study-session state file
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
        cs_mod.SessionLocal = self._orig_cs_session

class TestAPIGetItems(TestAPIBase):
    def test_get_items_returns_200(self):
        resp = self.client.get('/api/v1/items')
        self.assertEqual(resp.status_code, 200)

    def test_get_items_response_shape(self):
        resp = self.client.get('/api/v1/items')
        data = json.loads(resp.data)
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['data'], list)

    def test_get_items_empty_db_returns_empty_list(self):
        resp = self.client.get('/api/v1/items')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['data'], [])

class TestAPICreateItem(TestAPIBase):
    def test_create_valid_item_returns_201(self):
        resp = self.client.post('/api/v1/items',
            data=json.dumps({'question': 'What is Python?', 'answer': 'A language.'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    def test_create_item_returns_id(self):
        resp = self.client.post('/api/v1/items',
            data=json.dumps({'question': 'Q?', 'answer': 'A.'}),
            content_type='application/json')
        data = json.loads(resp.data)
        self.assertIn('data', data)
        self.assertIn('id', data['data'])

    def test_create_item_then_retrieve(self):
        self.client.post('/api/v1/items',
            data=json.dumps({'question': 'What is a decorator?', 'answer': 'A wrapper.'}),
            content_type='application/json')
        resp = self.client.get('/api/v1/items')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['data'][0]['question'], 'What is a decorator?')

class TestAPIBrowserIngest(TestAPIBase):
    def test_ingest_saves_concepts(self):
        resp = self.client.post('/api/v1/ingest',
            data=json.dumps({
                'text': ('The mitochondria is the powerhouse of the cell. '
                         'Cellular respiration converts glucose into ATP '
                         'through the Krebs cycle and oxidative phosphorylation. '
                         'This process produces the energy currency of the cell.'),
                'title': 'Biology notes'
            }),
            content_type='application/json')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.assertGreater(data['concepts_saved'], 0)
        self.assertIn('keywords', data)

    def test_ingest_rejects_short_text(self):
        resp = self.client.post('/api/v1/ingest',
            data=json.dumps({'text': 'hi', 'title': 'x'}),
            content_type='application/json')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('skipped', data['message'])

    def test_ingest_requires_text_field(self):
        resp = self.client.post('/api/v1/ingest',
            data=json.dumps({'title': 'x'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)

class TestAPIRecordReview(TestAPIBase):
    def test_record_review_valid(self):
        resp = self.client.post('/api/v1/items',
            data=json.dumps({'question': 'Q?', 'answer': 'A.'}),
            content_type='application/json')
        item_id = json.loads(resp.data)['data']['id']

        resp = self.client.post('/api/v1/reviews',
            data=json.dumps({'item_id': item_id, 'quality': 4}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)

class TestAPISessions(TestAPIBase):
    """Phase 9: study-session toggle endpoints."""

    def test_status_defaults_inactive(self):
        resp = self.client.get('/api/v1/session/status')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIs(data['data']['active'], False)

    def test_start_activates_session(self):
        resp = self.client.post('/api/v1/session/start')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.assertIs(data['data']['active'], True)

        status = json.loads(self.client.get('/api/v1/session/status').data)
        self.assertIs(status['data']['active'], True)

    def test_stop_deactivates_session(self):
        self.client.post('/api/v1/session/start')
        resp = self.client.post('/api/v1/session/stop')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIs(data['data']['active'], False)

    def test_start_stop_are_idempotent(self):
        self.client.post('/api/v1/session/start')
        data = json.loads(self.client.post('/api/v1/session/start').data)
        self.assertIs(data['data']['active'], True)

        self.client.post('/api/v1/session/stop')
        data = json.loads(self.client.post('/api/v1/session/stop').data)
        self.assertIs(data['data']['active'], False)

    def test_status_reports_elapsed_while_active(self):
        self.client.post('/api/v1/session/start')
        status = json.loads(self.client.get('/api/v1/session/status').data)
        self.assertGreaterEqual(status['data']['elapsed_seconds'], 0)

if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main(verbosity=2)
