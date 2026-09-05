# -*- coding: ascii -*-
"""F-2 regression tests for the browser-ingest context contract.

The context persisted next to extracted concepts is the sanitized capture BODY
text (validation cleaned_text) - never the literal 'ocr' token or the window
title (which used to be stored as 'browser:<title>').
"""

import json
import unittest

from tracker_app.web.app import app
from tracker_app.web.api import _sanitize_title
import tracker_app.tracking.keyword_extractor as ke_mod
import tracker_app.learning.text_quality_validator as tq_mod
import tracker_app.learning.concept_scheduler as cs_mod


def _fake_extract_concepts(text, top_n=15):
    return {"python": 0.9, "decorator": 0.7}


class _FakeScheduler:
    def __init__(self):
        self.added = []

    def add_concept(self, **kwargs):
        self.added.append(kwargs)
        return True


class TestSanitizeTitleUnit(unittest.TestCase):
    def test_strips_c0_controls(self):
        self.assertEqual(_sanitize_title("a\x00b\x01c"), "abc")

    def test_strips_escapes_del_and_c1(self):
        self.assertEqual(_sanitize_title("\x1b[31mred\x7f\x9c"), "[31mred")

    def test_collapses_whitespace_runs(self):
        self.assertEqual(_sanitize_title("  hello\n\t  world "), "hello world")

    def test_keeps_printable_unicode(self):
        self.assertEqual(
            _sanitize_title("Pok\u00e9mon GO \u2014 \u65e5\u672c\u8a9e"),
            "Pok\u00e9mon GO \u2014 \u65e5\u672c\u8a9e",
        )

    def test_empty_and_none(self):
        self.assertEqual(_sanitize_title(""), "")
        self.assertEqual(_sanitize_title(None), "")


class TestBrowserIngestTitleSanitised(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.scheduler = _FakeScheduler()
        self._patch_ke = None
        self._patch_tq = None
        self._patch_cs = None
        self._patch_kg = None

    def _patch_heavy_deps(self, cleaned_text="python decorators"):
        from unittest import mock

        self._patch_ke = mock.patch.object(ke_mod, "extract_concepts", side_effect=_fake_extract_concepts)
        self._patch_tq = mock.patch.object(
            tq_mod,
            "validate_and_clean_extraction",
            return_value={"is_useful": True, "cleaned_text": cleaned_text},
        )
        self._patch_cs = mock.patch.object(cs_mod, "ConceptScheduler", return_value=self.scheduler)
        # The ingest route records co-occurrence edges via record_capture_window;
        # keep this test hermetic (no real knowledge graph file involved).
        self._patch_kg = mock.patch(
            "tracker_app.tracking.knowledge_graph.record_capture_window",
            lambda concepts: None,
        )
        self._patch_ke.start()
        self._patch_tq.start()
        self._patch_cs.start()
        self._patch_kg.start()

    def tearDown(self):
        for p in (self._patch_ke, self._patch_tq, self._patch_cs, self._patch_kg):
            if p is not None:
                p.stop()

    def _ingest(self, title):
        return self.client.post(
            "/api/v1/ingest",
            data=json.dumps({"text": "Python decorators explained step by step guide", "title": title}),
            content_type="application/json",
        )

    def test_control_chars_in_title_never_reach_context(self):
        self._patch_heavy_deps()
        title = "ChatGPT\x1b[31m answer\n\t guide"
        resp = self._ingest(title)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.scheduler.added), 2)
        for call in self.scheduler.added:
            ctx = call["context"]
            self.assertEqual(ctx, "python decorators")
            self.assertNotIn("\x1b", ctx)
            self.assertNotIn("\n", ctx)
            self.assertNotIn("\t", ctx)
            self.assertNotIn("browser:", ctx)

    def test_body_text_reaches_context_not_title(self):
        self._patch_heavy_deps()
        resp = self._ingest("Clean\x00 Title")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.scheduler.added[0]["context"], "python decorators")

    def test_ingest_does_not_fabricate_attention(self):
        self._patch_heavy_deps()
        resp = self._ingest("A Title")
        self.assertEqual(resp.status_code, 200)
        for call in self.scheduler.added:
            self.assertNotIn("attention_at_encoding", call)

    def test_context_is_full_excerpt_not_truncated(self):
        long_text = " ".join(["word"] * 40)
        self._patch_heavy_deps(cleaned_text=long_text)
        resp = self._ingest("A Title")
        self.assertEqual(resp.status_code, 200)
        for call in self.scheduler.added:
            self.assertEqual(call["context"], long_text)
            self.assertGreater(len(call["context"]), 80)

    def test_missing_title_keeps_body_context(self):
        self._patch_heavy_deps()
        resp = self._ingest(None)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.scheduler.added[0]["context"], "python decorators")
