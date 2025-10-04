import sqlite3
from config import DB_PATH

def migrate_multi_modal_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if memory_score column already exists
    c.execute("PRAGMA table_info(multi_modal_logs)")
    columns = [col[1] for col in c.fetchall()]

    if "memory_score" not in columns:
        print("Adding memory_score column to multi_modal_logs...")
        c.execute("ALTER TABLE multi_modal_logs ADD COLUMN memory_score REAL DEFAULT 0.0")
        conn.commit()
        print("Migration complete: memory_score column added.")
    else:
        print("memory_score column already exists. No migration needed.")

    conn.close()


if __name__ == "__main__":
    migrate_multi_modal_logs()
