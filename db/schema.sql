-- SQL schema for Forgotten Knowledge Tracker database
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ts TEXT,
    end_ts TEXT,
    app_name TEXT,
    window_title TEXT,
    interaction_rate REAL
);

CREATE TABLE IF NOT EXISTS ocr_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    raw_text TEXT,
    keywords TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

-- More tables will be added for audio, video, memory, quizzes

CREATE TABLE IF NOT EXISTS audio_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    audio_label TEXT,
    confidence REAL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS video_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    attentiveness_score INTEGER,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
