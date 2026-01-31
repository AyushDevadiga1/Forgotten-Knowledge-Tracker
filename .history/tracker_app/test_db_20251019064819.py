# patch_sessions_iso.py
import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH

def fix_zero_duration_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, start_ts, end_ts FROM sessions")
    sessions = c.fetchall()

    updated_count = 0

    for sid, start_ts, end_ts in sessions:
        try:
            # Use fromisoformat to parse timestamps with microseconds
            start_dt = datetime.fromisoformat(start_ts)
            end_dt = datetime.fromisoformat(end_ts)
            
            if start_dt >= end_dt:
                new_end = start_dt + timedelta(minutes=1)
                c.execute(
                    "UPDATE sessions SET end_ts=? WHERE id=?", 
                    (new_end.isoformat(sep=' '), sid)  # Save in standard "YYYY-MM-DD HH:MM:SS" format
                )
                updated_count += 1
        except Exception as e:
            print(f"Error processing session {sid}: {e}")

    conn.commit()
    conn.close()
    print(f"Patched {updated_count} zero-duration sessions.")

if __name__ == "__main__":
    fix_zero_duration_sessions()
