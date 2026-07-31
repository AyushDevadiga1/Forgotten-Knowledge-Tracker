import sqlite3
from tracker_app.config import DB_PATH
DB_PATH  # change if your DB file has another name

def print_all_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    if not tables:
        print("⚠️ No tables found in database.")
        return

    for table_name, in tables:
        print(f"\n📌 Table: {table_name}")
        print("-" * 40)

        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            # Fetch column names
            col_names = [description[0] for description in cursor.description]
            print(" | ".join(col_names))
            print("-" * 40)

            if rows:
                for row in rows:
                    print(row)
            else:
                print("⚠️ No data in this table.")

        except Exception as e:
            print(f"❌ Error reading table {table_name}: {e}")

    conn.close()


if __name__ == "__main__":
    print("🔍 Printing all database contents...\n")
    print_all_tables()
