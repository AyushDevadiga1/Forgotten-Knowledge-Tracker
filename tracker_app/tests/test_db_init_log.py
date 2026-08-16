"""Regression tests for L-1: init_db logs the real ORM schema.

The log message was a hardcoded list of table names. It must be generated
from Base.metadata.sorted_tables so it can never drift from the schema.
"""

import logging

import pytest

from tracker_app.db import db_module, models
from tracker_app.db.models import Base


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("FKT_TEST_DB", str(tmp_path / "sessions.db"))
    monkeypatch.setattr(models, "_engine", None)
    monkeypatch.setattr(models, "_SessionLocal", None)
    yield
    engine = models._engine
    if engine is not None:
        engine.dispose()
    monkeypatch.setattr(models, "_engine", None)


def test_init_db_logs_joined_sorted_tables(isolated_db, caplog):
    with caplog.at_level(logging.INFO, logger="Database"):
        db_module.init_db()

    records = [r for r in caplog.records
               if r.name == "Database" and "tables constructed" in r.message]
    assert records, "init_db must log the constructed tables"
    expected = ", ".join(t.name for t in Base.metadata.sorted_tables)
    assert expected in records[0].message


def test_init_db_log_lists_every_orm_table(isolated_db, caplog):
    with caplog.at_level(logging.INFO, logger="Database"):
        db_module.init_db()

    records = [r for r in caplog.records
               if r.name == "Database" and "tables constructed" in r.message]
    assert records
    msg = records[0].message
    for table in Base.metadata.sorted_tables:
        assert table.name in msg
