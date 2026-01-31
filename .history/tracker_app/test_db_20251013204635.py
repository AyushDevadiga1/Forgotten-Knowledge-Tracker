import sqlite3
from config import DB_PATH

def reset_all_tables():
    conn = sqlite3.connect(DB_PATH)
    print([row for row in conn.execute("SELECT * FROM sessions LIMIT 5")])
    conn.close()


if __name__ == "__main__":
    reset_all_tables()
