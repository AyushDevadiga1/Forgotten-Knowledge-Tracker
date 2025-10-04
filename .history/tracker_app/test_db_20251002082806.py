# export_combined_logs.py
import sqlite3
import csv
from config import DB_PATH
from datetime import datetime

def fetch_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch sessions
    c.execute("SELECT * FROM sessions")
    sessions = c.fetchall()
    session_cols = [desc[0] for desc in c.description]

    # Fetch multi-modal logs
    c.execute("SELECT * FROM multi_modal_logs")
    logs = c.fetchall()
    log_cols = [desc[0] for desc in c.description]

    conn.close()
    return sessions, session_cols, logs, log_cols

def merge_sessions_logs(sessions, session_cols, logs, log_cols):
    merged_rows = []

    for log in logs:
        log_dict = dict(zip(log_cols, log))

        # Find a matching session by window title and closest timestamp
        matching_session = None
        min_time_diff = float('inf')

        for session in sessions:
            session_dict = dict(zip(session_cols, session))

            if session_dict['window_title'] == log_dict['window_title'] and session_dict['start_ts']:
                # Compute time difference
                session_time = datetime.strptime(session_dict['start_ts'], "%Y-%m-%d %H:%M:%S")
                log_time = datetime.strptime(log_dict['timestamp'], "%Y-%m-%d %H:%M:%S")
                time_diff = abs((log_time - session_time).total_seconds())

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    matching_session = session_dict

        merged_row = {**(matching_session or {}), **log_dict}
        merged_rows.append(merged_row)

    return merged_rows

def save_to_csv(merged_rows, filename="combined_logs.csv"):
    if not merged_rows:
        print("No data to save.")
        return

    # Get all column names
    col_names = merged_rows[0].keys()

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=col_names)
        writer.writeheader()
        writer.writerows(merged_rows)

    print(f"Combined logs exported to {filename}")

if __name__ == "__main__":
    sessions, session_cols, logs, log_cols = fetch_tables()
    merged_rows = merge_sessions_logs(sessions, session_cols, logs, log_cols)
    save_to_csv(merged_rows)
