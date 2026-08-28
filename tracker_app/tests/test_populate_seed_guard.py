"""Seed guard (P7/D6): populate.py must refuse to write unless FKT_SEED=1."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_populate(env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "tracker_app.tools.populate"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
    )


def test_populate_without_fkt_seed_writes_nothing(tmp_path):
    db_file = str(tmp_path / "unseeded.db")
    proc = _run_populate({"FKT_TEST_DB": db_file})
    assert proc.returncode == 0, proc.stderr
    assert "Seeding refused" in proc.stdout
    assert "FKT_SEED=1" in proc.stdout
    assert not Path(db_file).exists(), "seed guard must not create any DB file"


def test_populate_marks_seeded_db(tmp_path):
    db_file = str(tmp_path / "seeded.db")
    proc = _run_populate({"FKT_TEST_DB": db_file, "FKT_SEED": "1"})
    assert proc.returncode == 0, proc.stderr
    conn = sqlite3.connect(db_file)
    try:
        marker = conn.execute("SELECT concept, memory_score FROM metrics WHERE concept = '__seed__'").fetchall()
    finally:
        conn.close()
    assert marker == [("__seed__", 0.0)]
