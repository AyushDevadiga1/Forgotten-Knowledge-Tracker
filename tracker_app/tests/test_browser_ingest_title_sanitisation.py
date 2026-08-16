# -*- coding: ascii -*-
"""F-2 regression tests: browser_ingest title sanitisation.

A title field with control characters (escapes, null bytes, newlines) must be
stripped of those characters and whitespace-collapsed before it reaches
ConceptEncounter.context_snippet.
"""

import json
import unittest

from tracker_app.web.app import app
from tracker_app.web.api import _sanitize_title
import tracker_app.tracking.keyword_extractor as ke_mod
import tracker_app.learning.text_quality_validator as tq_mod
import tracker_app.learning.concept_scheduler as cs_mod


class _FakeExtractor:
    def get_keyword_scores_dict(self, text, top_n=15):
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
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.scheduler = _FakeScheduler()
        self._patch_ke = None
        self._patch_tq = None
        self._patch_cs = None

    def _patch_heavy_deps(self):
        from unittest import mock
        self._patch_ke = mock.patch.object(ke_mod, 'get_keyword_extractor',
                                           return_value=_FakeExtractor())
        self._patch_tq = mock.patch.object(
            tq_mod, 'validate_and_clean_extraction',
            return_value={'is_useful': True, 'cleaned_text': 'python decorators'})
        self._patch_cs = mock.patch.object(cs_mod, 'ConceptScheduler',
                                           return_value=self.scheduler)
        self._patch_ke.start()
        self._patch_tq.start()
        self._patch_cs.start()

    def tearDown(self):
        for p in (self._patch_ke, self._patch_tq, self._patch_cs):
            if p is not None:
                p.stop()

    def _ingest(self, title):
        return self.client.post(
            '/api/v1/ingest',
            data=json.dumps({'text': 'Python decorators explained step by step guide',
                             'title': title}),
            content_type='application/json')

    def test_control_chars_stripped_before_context(self):
        self._patch_heavy_deps()
        title = "ChatGPT\x1b[31m answer\n\t guide"
        resp = self._ingest(title)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.scheduler.added), 2)
        for call in self.scheduler.added:
            ctx = call['context']
            self.assertTrue(ctx.startswith('browser:'))
            self.assertNotIn('\x1b', ctx)
            self.assertNotIn('\n', ctx)
            self.assertNotIn('\t', ctx)
            self.assertNotIn('\x00', ctx)

    def test_sanitised_title_reaches_context(self):
        self._patch_heavy_deps()
        resp = self._ingest("Clean\x00 Title")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.scheduler.added[0]['context'], "browser:Clean Title")

    def test_title_truncated_to_80_chars(self):
        self._patch_heavy_deps()
        long_title = "word-" * 40
        self._ingest(long_title)
        ctx = self.scheduler.added[0]['context']
        self.assertTrue(ctx.startswith('browser:'))
        self.assertLessEqual(len(ctx) - len('browser:'), 80)

    def test_missing_title_is_empty_not_crash(self):
        self._patch_heavy_deps()
        resp = self._ingest(None)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.scheduler.added[0]['context'], "browser:")
