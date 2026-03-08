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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.web.app import app
from tracker_app.db import models
from tracker_app.db.models import Base, IntentPrediction

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
        
        Base.metadata.create_all(bind=self.test_engine)

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
        self.client = app.test_client()

    def tearDown(self):
        Base.metadata.drop_all(bind=self.test_engine)
        models.engine = self.orig_engine
        models.SessionLocal = self.orig_session

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

if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main(verbosity=2)
