from core.db_module import init_db, init_multi_modal_db, init_memory_decay_db
import sqlite3
from config import DB_PATH

def test_tables():
    init_db()
    init_multi_modal_db()
    init_memory_decay_db()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check tables
    tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables:", tables)

    # Check memory_decay columns
    columns = [row[1] for row in c.execute("PRAGMA table_info(memory_decay)").fetchall()]
    print("memory_decay columns:", columns)

    conn.close()

if __name__ == "__main__":
    test_tables()
