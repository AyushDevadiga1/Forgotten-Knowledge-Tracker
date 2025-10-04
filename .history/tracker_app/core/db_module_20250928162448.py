def log_session_data(session_data):
    """
    Write a snapshot of session_data to the DB.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = session_data.get("last_update").strftime("%Y-%m-%d %H:%M:%S") if session_data.get("last_update") else None
    app_name = session_data.get("window_title", "")
    interaction_rate = session_data.get("interaction_rate", 0)

    c.execute("""INSERT INTO sessions 
                 (start_ts, end_ts, app_name, window_title, interaction_rate)
                 VALUES (?, ?, ?, ?, ?)""",
              (ts, ts, app_name, app_name, interaction_rate))
    conn.commit()
    conn.close()
