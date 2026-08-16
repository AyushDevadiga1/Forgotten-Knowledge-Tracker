# -*- coding: ascii -*-
"""F-1 regression tests: flask-limiter wiring + 429 on breach.

The limiter must be attached to the real web app, enabled by default, and
exempt while Flask is in TESTING mode so the test harness is never throttled.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tracker_app.web.app import app, limiter
from tracker_app.db import models
from tracker_app.db.models import Base
import tracker_app.learning.concept_scheduler as cs_mod


class RateLimitBase(unittest.TestCase):
    def setUp(self):
        self.test_engine = create_engine('sqlite:///:memory:')
        self.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.test_engine)

        self.orig_engine = models.engine
        self.orig_session = models.SessionLocal
        models.engine = self.test_engine
        models.SessionLocal = self.TestingSessionLocal

        self._orig_cs_session = cs_mod.SessionLocal
        cs_mod.SessionLocal = self.TestingSessionLocal

        Base.metadata.create_all(bind=self.test_engine)

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def tearDown(self):
        Base.metadata.drop_all(bind=self.test_engine)
        models.engine = self.orig_engine
        models.SessionLocal = self.orig_session
        cs_mod.SessionLocal = self._orig_cs_session
        app.config['TESTING'] = True


class TestLimiterWiring(RateLimitBase):
    def test_limiter_attached_to_app_and_enabled(self):
        self.assertIn(limiter, app.extensions['limiter'])
        self.assertTrue(limiter.enabled)

    def test_requests_pass_under_testing(self):
        for _ in range(65):
            resp = self.client.get('/api/v1/items')
            self.assertEqual(resp.status_code, 200)

    def test_requests_exceed_default_limit_return_429(self):
        app.config['TESTING'] = False
        try:
            if limiter.storage is not None:
                limiter.storage.reset()
            codes = [self.client.get('/api/v1/items').status_code
                     for _ in range(61)]
            self.assertEqual(codes[-1], 429)
            self.assertEqual(sum(1 for c in codes if c == 200), 60)
        finally:
            app.config['TESTING'] = True

    def test_limit_recovers_after_storage_reset(self):
        app.config['TESTING'] = False
        try:
            if limiter.storage is not None:
                limiter.storage.reset()
            for _ in range(61):
                self.client.get('/api/v1/items')
            self.assertEqual(self.client.get('/api/v1/items').status_code, 429)
            if limiter.storage is not None:
                limiter.storage.reset()
            self.assertEqual(self.client.get('/api/v1/items').status_code, 200)
        finally:
            app.config['TESTING'] = True


def test_limiter_disable_via_env():
    """RATELIMIT_ENABLED=false must turn the limiter off at boot."""
    root = str(Path(__file__).parent.parent.parent)
    env = {k: v for k, v in os.environ.items()
           if k not in ('SECRET_KEY', 'DEBUG')}
    env['DEBUG'] = 'true'
    env['RATELIMIT_ENABLED'] = 'false'
    code = 'from tracker_app.web.app import limiter; print(limiter.enabled)'
    r = subprocess.run(
        [sys.executable, '-c', code], cwd=root, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == 'False'
