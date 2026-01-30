# core/session_manager.py
import sqlite3
from datetime import datetime
from config import DB_PATH

def create_session():
    """Create a new session dictionary"""
    return {
        "window_title": "",
        "interaction_rate": 0,
        "ocr_keywords": {},
        "audio_label": "silence",
        "attention_score": 0,
        "intent_label": "",
        "intent_confidence": 0.0,
        "start_time": datetime.now(),
        "last_update": datetime.now()
    }

def update_session(session, key, value):
    """Update session data with timestamp"""
    session[key] = value
    session["last_update"] = datetime.now()

def log_session(start_ts=None, end_ts=None, app_name=None, window_title=None, 
                interaction_rate=0, audio_label=None, intent_label=None, 
                intent_confidence=None):
    """Log session to database with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        start_ts = start_ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        end_ts = end_ts or start_ts

        c.execute('''
            INSERT INTO sessions 
            (start_ts, end_ts, app_name, window_title, interaction_rate, 
             audio_label, intent_label, intent_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(start_ts),
            str(end_ts),
            str(app_name) if app_name else None,
            str(window_title) if window_title else None,
            float(interaction_rate),
            str(audio_label) if audio_label else None,
            str(intent_label) if intent_label else None,
            float(intent_confidence) if intent_confidence else 0.0
        ))

        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error logging session: {e}")
        return False

def get_recent_sessions(limit=10):
    """Get recent sessions from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''
            SELECT start_ts, app_name, window_title, interaction_rate, 
                   audio_label, intent_label, intent_confidence
            FROM sessions 
            ORDER BY start_ts DESC 
            LIMIT ?
        ''', (int(limit),))
        
        rows = c.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append({
                'start_ts': row[0],
                'app_name': row[1],
                'window_title': row[2],
                'interaction_rate': row[3],
                'audio_label': row[4],
                'intent_label': row[5],
                'intent_confidence': row[6]
            })
            
        return sessions
        
    except Exception as e:
        print(f"Error getting recent sessions: {e}")
        return []

def get_session_stats(timeframe_hours=24):
    """Get session statistics for the specified timeframe"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Calculate cutoff time
        cutoff_time = datetime.now() - datetime.timedelta(hours=timeframe_hours)
        cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get basic stats
        c.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                AVG(interaction_rate) as avg_interaction,
                COUNT(DISTINCT app_name) as unique_apps,
                SUM(CASE WHEN intent_label = 'studying' THEN 1 ELSE 0 END) as studying_sessions
            FROM sessions 
            WHERE start_ts >= ?
        ''', (cutoff_str,))
        
        stats_row = c.fetchone()
        
        # Get most used apps
        c.execute('''
            SELECT app_name, COUNT(*) as session_count
            FROM sessions 
            WHERE start_ts >= ? AND app_name IS NOT NULL
            GROUP BY app_name 
            ORDER BY session_count DESC 
            LIMIT 5
        ''', (cutoff_str,))
        
        top_apps = c.fetchall()
        
        conn.close()
        
        if stats_row:
            stats = {
                'total_sessions': stats_row[0],
                'avg_interaction': float(stats_row[1] or 0),
                'unique_apps': stats_row[2],
                'studying_sessions': stats_row[3],
                'top_apps': [{'app': app[0], 'sessions': app[1]} for app in top_apps]
            }
            return stats
        else:
            return None
            
    except Exception as e:
        print(f"Error getting session stats: {e}")
        return None

# Example usage and testing
if __name__ == "__main__":
    # Test session creation
    session = create_session()
    update_session(session, "window_title", "Test Application")
    update_session(session, "interaction_rate", 5.2)
    
    print("Current session:", session)
    
    # Test logging
    success = log_session(
        app_name="Test App",
        window_title="Test Window",
        interaction_rate=5.2,
        audio_label="silence",
        intent_label="passive",
        intent_confidence=0.6
    )
    
    print(f"Session logged: {success}")
    
    # Get recent sessions
    recent = get_recent_sessions(5)
    print("Recent sessions:", recent)
    
    # Get stats
    stats = get_session_stats(24)
    print("24h stats:", stats)