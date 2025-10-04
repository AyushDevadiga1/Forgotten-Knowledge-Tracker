# export_logs.py
import sqlite3
import csv
from config import DB_PATH

def export_table_to_csv(table_name, csv_file):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(f"SELECT * FROM {table_name}")
    rows = c.fetchall()

    # Get column names
    col_names = [description[0] for description in c.description]

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(col_names)  # header
        writer.writerows(rows)

    conn.close()
    print(f"{table_name} exported to {csv_file}")

if __name__ == "__main__":
    export_table_to_csv("sessions", "sessions_export.csv")
    export_table_to_csv("multi_modal_logs", "multi_modal_logs_export.csv")
