import sqlite3
import csv
from datetime import datetime
from config import DB_PATH

def fetch_data():
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
        log_time = None
        if log_dict['timestamp']:
            try:
                log_time = datetime.fromisoformat(log_dict['timestamp'])
            except Exception:
                log_time = None

        # Find matching session
        matched_session = None
        for session in sessions:
            session_dict = dict(zip(session_cols, session))
            if session_dict['start_ts']:
                try:
                    session_time = datetime.fromisoformat(session_dict['start_ts'])
                except Exception:
                    continue

                if session_time == log_time:
                    matched_session = session_dict
                    break

        # Merge dictionaries safely
        merged = {**{k: "N/A" for k in session_cols}, **{k: "N/A" for k in log_cols}}
        if matched_session:
            merged.update(matched_session)
        merged.update(log_dict)

        merged_rows.append(merged)

    return merged_rows

def export_csv(filename="merged_logs.csv"):
    sessions, session_cols, logs, log_cols = fetch_data()
    merged_rows = merge_sessions_logs(sessions, session_cols, logs, log_cols)

    # Write CSV
    all_cols = list(merged_rows[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols)
        writer.writeheader()
        for row in merged_rows:
            writer.writerow(row)

    print(f"CSV exported: {filename}")

if __name__ == "__main__":
    export_csv()
