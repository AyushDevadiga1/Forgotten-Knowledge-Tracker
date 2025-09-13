from flask import Flask, render_template, jsonify, request
import sqlite3
import json
from datetime import datetime
import os
import sys

# Add the parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration
try:
    from config import DB_PATH, WEB_HOST, WEB_PORT, DEBUG
except ImportError:
    # Fallback if config doesn't exist
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                          'data', 'tracking.db')
    WEB_HOST = '0.0.0.0'
    WEB_PORT = 5000
    DEBUG = True

app = Flask(__name__, 
           static_folder='static',
           static_url_path='/static',
           template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize database manager
try:
    from core.database import DatabaseManager
    db = DatabaseManager(DB_PATH)
except ImportError:
    print("Warning: Could not import core modules. Using direct SQLite access.")
    db = None

# Initialize search engine
try:
    from core.search_engine import knowledge_search
    knowledge_search.db_path = DB_PATH
except ImportError:
    print("Warning: Search engine not available")
    knowledge_search = None

def get_db_connection():
    """Get direct SQLite connection"""
    return sqlite3.connect(DB_PATH)

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        # Get statistics for the dashboard
        stats = get_system_stats()
        
        # Get recent activity
        recent_activity = get_recent_activity(limit=10)
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_activity=recent_activity,
                             now=datetime.now().timestamp())  # Add timestamp for cache busting
    except Exception as e:
        print(f"Error rendering dashboard: {e}")
        # Fallback to basic rendering if template fails
        stats = get_system_stats()
        recent_activity = get_recent_activity(limit=10)
        return f"""
        <html>
        <head><title>Forgotten Knowledge Tracker</title></head>
        <body>
            <h1>Forgotten Knowledge Tracker</h1>
            <p>Error loading template: {e}</p>
            <p>Stats: {stats}</p>
        </body>
        </html>
        """

@app.route('/test-static')
def test_static():
    """Test route to verify static files are working"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Static File Test</title>
        <link href="/static/css/style.css" rel="stylesheet">
    </head>
    <body style="padding: 20px;">
        <div class="stats-card stats-card-1" style="padding: 20px;">
            <h3>Static File Test</h3>
            <p>If this has a gradient background, CSS is working!</p>
        </div>
        <p><a href="/">Back to Dashboard</a></p>
    </body>
    </html>
    '''

@app.route('/debug')
def debug_info():
    """Debug information page"""
    stats = get_system_stats()
    recent_activity = get_recent_activity(limit=5)
    
    return f"""
    <html>
    <head><title>Debug Info</title></head>
    <body>
        <h1>Debug Information</h1>
        <h2>Stats:</h2>
        <pre>{json.dumps(stats, indent=2)}</pre>
        
        <h2>Recent Activity:</h2>
        <pre>{json.dumps(recent_activity, indent=2)}</pre>
        
        <h2>Static Files:</h2>
        <ul>
            <li><a href="/static/css/style.css">CSS File</a></li>
            <li><a href="/static/js/dashboard.js">JS File</a></li>
        </ul>
        
        <p><a href="/">Back to Dashboard</a></p>
    </body>
    </html>
    """

@app.route('/search')
def search():
    """Search endpoint"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    if knowledge_search:
        results = knowledge_search.search_all(query, limit=20)
        return jsonify(results)
    else:
        # Fallback search
        return jsonify([])

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    stats = get_system_stats()
    return jsonify(stats)

@app.route('/api/activity')
def api_activity():
    """API endpoint for recent activity"""
    limit = request.args.get('limit', 10, type=int)
    activity = get_recent_activity(limit)
    return jsonify(activity)

@app.route('/api/audio')
def api_audio():
    """API endpoint for audio recordings"""
    limit = request.args.get('limit', 10, type=int)
    
    try:
        if db:
            recordings = db.get_audio_recordings(limit)
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM audio_recordings ORDER BY timestamp DESC LIMIT ?', (limit,))
            recordings = []
            for row in cursor.fetchall():
                recordings.append({
                    'id': row[0],
                    'file_path': row[1],
                    'timestamp': row[2],
                    'duration': row[3],
                    'transcribed_text': row[4],
                    'confidence': row[5],
                    'word_count': row[6],
                    'keywords': json.loads(row[7]) if row[7] else [],
                    'is_educational': bool(row[8]) if row[8] is not None else False
                })
            conn.close()
        
        return jsonify(recordings)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/screenshots')
def api_screenshots():
    """API endpoint for screenshots"""
    limit = request.args.get('limit', 10, type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.file_path, s.timestamp, s.window_title, s.app_name,
                   o.extracted_text, o.confidence, o.word_count
            FROM screenshots s
            LEFT JOIN ocr_results o ON s.id = o.screenshot_id
            ORDER BY s.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        screenshots = []
        for row in cursor.fetchall():
            screenshots.append({
                'id': row[0],
                'file_path': row[1],
                'timestamp': row[2],
                'window_title': row[3],
                'app_name': row[4],
                'extracted_text': row[5],
                'confidence': row[6] if row[6] is not None else 0,
                'word_count': row[7] if row[7] is not None else 0
            })
        
        conn.close()
        return jsonify(screenshots)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_system_stats():
    """Get comprehensive system statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total tracking time
        cursor.execute('SELECT SUM(duration) FROM window_history')
        total_seconds = cursor.fetchone()[0] or 0
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        # Get counts
        cursor.execute('SELECT COUNT(*) FROM screenshots')
        screenshot_count = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM ocr_results')
        ocr_count = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM audio_recordings')
        audio_count = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM window_history')
        window_count = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(duration) FROM audio_recordings')
        audio_duration = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_tracking_time': f"{hours}h {minutes}m",
            'screenshot_count': screenshot_count,
            'ocr_count': ocr_count,
            'audio_recordings': audio_count,
            'audio_duration': audio_duration,
            'window_entries': window_count
        }
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            'total_tracking_time': "0h 0m",
            'screenshot_count': 0,
            'ocr_count': 0,
            'audio_recordings': 0,
            'audio_duration': 0,
            'window_entries': 0,
            'error': str(e)
        }

def get_recent_activity(limit=10):
    """Get recent activity across all sources"""
    activity = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent window activity
        cursor.execute('''
            SELECT title, app, start_time, duration 
            FROM window_history 
            ORDER BY start_time DESC 
            LIMIT ?
        ''', (limit,))
        
        for title, app, timestamp, duration in cursor.fetchall():
            activity.append({
                'type': 'window',
                'timestamp': timestamp,
                'title': title,
                'app': app,
                'duration': duration
            })
        
        # Get recent audio recordings
        cursor.execute('''
            SELECT timestamp, file_path, duration 
            FROM audio_recordings 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        for timestamp, file_path, duration in cursor.fetchall():
            activity.append({
                'type': 'audio',
                'timestamp': timestamp,
                'title': f"Audio: {os.path.basename(file_path)}",
                'duration': duration
            })
        
        conn.close()
        
        # Sort by timestamp (newest first)
        activity.sort(key=lambda x: x['timestamp'], reverse=True)
        return activity[:limit]
        
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return []
@app.route('/test-css')
def test_css():
    """Test if CSS is loading correctly"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CSS Test</title>
        <link href="/static/css/style.css" rel="stylesheet">
        <style>
            .test-result { padding: 20px; margin: 20px; border-radius: 10px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="google-navbar">
            <h3>CSS Loading Test</h3>
        </div>
        <div class="container-fluid">
            <div class="stats-card stats-card-1">
                <div class="text-center">
                    <h5>Test Card</h5>
                    <h3>If styled, CSS works!</h3>
                </div>
            </div>
            <div id="testResult" class="test-result">
                Testing CSS loading...
            </div>
        </div>
        <script>
            setTimeout(() => {
                const testCard = document.querySelector('.stats-card');
                const style = window.getComputedStyle(testCard);
                if (style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.borderRadius === '12px') {
                    document.getElementById('testResult').className = 'test-result success';
                    document.getElementById('testResult').innerHTML = '✅ CSS is loading correctly!';
                } else {
                    document.getElementById('testResult').className = 'test-result error';
                    document.getElementById('testResult').innerHTML = '❌ CSS is not loading properly';
                }
            }, 1000);
        </script>
    </body>
    </html>
    '''
@app.route('/debug-data')
def debug_data():
    """Debug data endpoint"""
    stats = get_system_stats()
    activity = get_recent_activity(limit=5)
    
    return jsonify({
        'stats': stats,
        'recent_activity': activity,
        'database_path': DB_PATH,
        'database_exists': os.path.exists(DB_PATH)
    })
if __name__ == '__main__':
    print(f"🌐 Starting web server on {WEB_HOST}:{WEB_PORT}")
    print(f"📊 Database path: {DB_PATH}")
    print(f"📁 Static files: {app.static_folder}")
    print(f"📝 Templates: {app.template_folder}")
    print(f"🔗 Test URLs:")
    print(f"   - Dashboard: http://{WEB_HOST}:{WEB_PORT}/")
    print(f"   - Static test: http://{WEB_HOST}:{WEB_PORT}/test-static")
    print(f"   - Debug info: http://{WEB_HOST}:{WEB_PORT}/debug")
    app.run(debug=DEBUG, host=WEB_HOST, port=WEB_PORT)