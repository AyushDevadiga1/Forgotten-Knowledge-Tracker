"""
Unit Tests: Flask API Endpoints
================================
Tests all API routes using Flask's test client (no real server needed).
Run: python -m pytest tracker_app/tests/test_api.py -v
"""

import unittest
import json
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestAPIGetItems(unittest.TestCase):

    def setUp(self):
        # Point tracker to a temp DB so tests don't affect real data
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()

        # Import app and both tracker instances
        from tracker_app.web.app import app, tracker
        from tracker_app.web.api import tracker as api_tracker
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for tests
        
        self.old_db_path = tracker.db_path
        tracker.db_path = self.tmp.name
        api_tracker.db_path = self.tmp.name
        tracker._init_database()

        self.client = app.test_client()

    def tearDown(self):
        import gc
        from tracker_app.web.app import tracker
        from tracker_app.web.api import tracker as api_tracker
        tracker.db_path = self.old_db_path
        api_tracker.db_path = self.old_db_path
        gc.collect()
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_get_items_returns_200(self):
        resp = self.client.get('/api/v1/items')
        self.assertEqual(resp.status_code, 200)

    def test_get_items_response_shape(self):
        """Response must have success, data (list), count."""
        resp = self.client.get('/api/v1/items')
        data = json.loads(resp.data)
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIn('count', data)
        self.assertIsInstance(data['data'], list)

    def test_get_items_empty_db_returns_empty_list(self):
        resp = self.client.get('/api/v1/items')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['data'], [])

    def test_get_items_invalid_limit_handled(self):
        """?limit=abc should not crash the server (return 400 or handle gracefully)."""
        resp = self.client.get('/api/v1/items?limit=abc')
        # Should be 400 (bad request), NOT 500 (server crash)
        self.assertNotEqual(resp.status_code, 500,
            "Invalid limit should not cause a 500 server error")

    def test_get_items_invalid_status_handled(self):
        """?status=NONSENSE should return empty list or 400, not 500."""
        resp = self.client.get('/api/v1/items?status=NONSENSE')
        self.assertNotEqual(resp.status_code, 500)

    def test_get_due_items_returns_200(self):
        resp = self.client.get('/api/v1/items/due')
        self.assertEqual(resp.status_code, 200)

    def test_get_stats_returns_200(self):
        resp = self.client.get('/api/v1/stats')
        self.assertEqual(resp.status_code, 200)

    def test_get_nonexistent_item_returns_404(self):
        resp = self.client.get('/api/v1/items/does-not-exist-xyz')
        self.assertEqual(resp.status_code, 404)


class TestAPICreateItem(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        from tracker_app.web.app import app, tracker
        from tracker_app.web.api import tracker as api_tracker
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.old_db_path = tracker.db_path
        tracker.db_path = self.tmp.name
        api_tracker.db_path = self.tmp.name
        tracker._init_database()

        self.client = app.test_client()

    def tearDown(self):
        import gc
        from tracker_app.web.app import tracker
        from tracker_app.web.api import tracker as api_tracker
        tracker.db_path = self.old_db_path
        api_tracker.db_path = self.old_db_path
        gc.collect()
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

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

    def test_create_item_missing_question_returns_400(self):
        """Missing question should return 400, not 500."""
        resp = self.client.post('/api/v1/items',
            data=json.dumps({'answer': 'A.'}),
            content_type='application/json')
        self.assertIn(resp.status_code, [400, 422],
            f"Missing question should return 400/422, got {resp.status_code}")

    def test_create_item_missing_answer_returns_400(self):
        """Missing answer should return 400, not 500."""
        resp = self.client.post('/api/v1/items',
            data=json.dumps({'question': 'Q?'}),
            content_type='application/json')
        self.assertIn(resp.status_code, [400, 422],
            f"Missing answer should return 400/422, got {resp.status_code}")

    def test_create_item_no_json_body_returns_400(self):
        """No JSON body at all should return 400, not 500."""
        resp = self.client.post('/api/v1/items',
            data='',
            content_type='application/json')
        self.assertNotEqual(resp.status_code, 500,
            "No JSON body should not cause 500")

    def test_create_item_then_retrieve(self):
        """Item created via POST should be retrievable via GET."""
        self.client.post('/api/v1/items',
            data=json.dumps({'question': 'What is a decorator?', 'answer': 'A function wrapper.'}),
            content_type='application/json')
        resp = self.client.get('/api/v1/items')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['data'][0]['question'], 'What is a decorator?')


class TestAPIRecordReview(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        from tracker_app.web.app import app, tracker
        from tracker_app.web.api import tracker as api_tracker
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.old_db_path = tracker.db_path
        tracker.db_path = self.tmp.name
        api_tracker.db_path = self.tmp.name
        tracker._init_database()
        
        self.client = app.test_client()

    def tearDown(self):
        import gc
        from tracker_app.web.app import tracker
        from tracker_app.web.api import tracker as api_tracker
        tracker.db_path = self.old_db_path
        api_tracker.db_path = self.old_db_path
        gc.collect()
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_record_review_valid(self):
        # Create an item first
        resp = self.client.post('/api/v1/items',
            data=json.dumps({'question': 'Q?', 'answer': 'A.'}),
            content_type='application/json')
        item_id = json.loads(resp.data)['data']['id']

        resp = self.client.post('/api/v1/reviews',
            data=json.dumps({'item_id': item_id, 'quality': 4}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    def test_record_review_no_body_returns_400(self):
        """No JSON body should not crash the server."""
        resp = self.client.post('/api/v1/reviews',
            data='', content_type='application/json')
        self.assertNotEqual(resp.status_code, 500,
            "No body for review should not cause 500")

    def test_record_review_invalid_quality_returns_400(self):
        """Quality outside 0-5 should return 400."""
        resp = self.client.post('/api/v1/reviews',
            data=json.dumps({'item_id': 'some-id', 'quality': 99}),
            content_type='application/json')
        self.assertIn(resp.status_code, [400, 422, 404])


if __name__ == '__main__':
    unittest.main(verbosity=2)
