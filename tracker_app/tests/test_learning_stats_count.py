"""Regression tests for L-2: get_learning_stats uses COUNT, not a full load.

Previously it computed len(LearningRepository.get_all_items(db)), loading
every row just to report a total. It must use get_total_count and never
materialize the whole table.
"""

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import tracker_app.learning.learning_tracker as lt
from tracker_app.db import models
from tracker_app.db.models import Base
from tracker_app.db.repository import LearningRepository


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(models, "_engine", engine)
    monkeypatch.setattr(models, "_SessionLocal", TestingSessionLocal)
    return TestingSessionLocal


def test_get_learning_stats_does_not_materialize_all_items(db, monkeypatch):
    calls = {"get_all_items": 0}

    def fake_get_all_items(sess):
        calls["get_all_items"] += 1
        return []

    monkeypatch.setattr(LearningRepository, "get_all_items", fake_get_all_items)

    stats = lt.LearningTracker().get_learning_stats()

    assert calls["get_all_items"] == 0
    assert stats["total_items"] == 0


def test_get_learning_stats_honors_get_total_count(db, monkeypatch):
    def boom(sess):
        raise AssertionError("get_all_items must not be called")

    monkeypatch.setattr(LearningRepository, "get_all_items", boom)
    monkeypatch.setattr(LearningRepository, "get_total_count", lambda db_: 42)

    stats = lt.LearningTracker().get_learning_stats()

    assert stats["total_items"] == 42
