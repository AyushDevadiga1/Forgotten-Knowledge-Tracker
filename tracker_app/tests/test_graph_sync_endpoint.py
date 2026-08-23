"""F-6 regression tests: POST /api/v1/graph/sync forces a DB->graph resync."""

import json
import unittest
from unittest import mock

from tracker_app.web.app import app
from tracker_app.tracking import knowledge_graph as kg


class GraphSyncEndpointTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_endpoint_calls_force_sync_and_returns_stats(self):
        with mock.patch.object(kg, "sync_db_to_graph", return_value={"nodes": 3, "edges": 2, "synced": 1}) as patched:
            resp = self.client.post("/api/v1/graph/sync")
        patched.assert_called_once_with(force=True)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"], {"nodes": 3, "edges": 2, "synced": 1})

    def test_endpoint_reports_empty_sync(self):
        with mock.patch.object(kg, "sync_db_to_graph", return_value={"nodes": 0, "edges": 0, "synced": 0}):
            resp = self.client.post("/api/v1/graph/sync")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["synced"], 0)
        self.assertEqual(data["data"]["nodes"], 0)

    def test_get_does_not_trigger_sync_and_post_does(self):
        # The SPA catch-all serves index.html for any unmatched GET, so a GET
        # must return HTML and never invoke the force-sync; only POST runs it.
        # Mock send_from_directory to avoid depending on frontend/dist existing.
        with mock.patch.object(kg, "sync_db_to_graph", return_value={"nodes": 0, "edges": 0, "synced": 0}) as patched:
            with mock.patch(
                "tracker_app.web.app.send_from_directory",
                return_value=("<html></html>", 200, {"Content-Type": "text/html"}),
            ):
                get_resp = self.client.get("/api/v1/graph/sync")
                self.assertEqual(get_resp.status_code, 200)
                self.assertIn("text/html", get_resp.content_type)
                patched.assert_not_called()
            post_resp = self.client.post("/api/v1/graph/sync")
        self.assertEqual(post_resp.status_code, 200)
        patched.assert_called_once_with(force=True)
