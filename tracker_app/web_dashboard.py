"""
Simple Web Dashboard for Learning Tracker

Lightweight dashboard using Flask for viewing progress and managing items
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from core.learning_tracker import LearningTracker
from core.sm2_memory_model import SM2Scheduler, format_next_review
from datetime import datetime, timedelta
import json

app = Flask(__name__)
tracker = LearningTracker()


# HTML Templates
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Learning Tracker Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        h1 { color: #333; font-size: 32px; }
        .subtitle { color: #666; margin-top: 5px; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
        .stat-card .number { font-size: 36px; font-weight: bold; color: #667eea; }
        .stat-card .subtitle { font-size: 12px; color: #999; margin-top: 5px; }
        
        .section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .section h2 { color: #333; margin-bottom: 20px; font-size: 24px; }
        
        .item-list {
            list-style: none;
        }
        .item-card {
            padding: 15px;
            border-left: 4px solid #667eea;
            background: #f8f9fa;
            margin-bottom: 10px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .item-card:hover { background: #f0f1f5; }
        
        .item-question { font-weight: 500; color: #333; }
        .item-meta { font-size: 12px; color: #999; margin-top: 5px; }
        .item-stats {
            text-align: right;
            display: flex;
            gap: 15px;
            align-items: center;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
        }
        
        .button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        .button:hover { background: #764ba2; }
        .button-secondary { background: #6c757d; }
        .button-secondary:hover { background: #5a6268; }
        
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-info { background: #d1ecf1; color: #0c5460; }
        
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        input, textarea, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-family: inherit;
        }
        textarea { resize: vertical; min-height: 80px; }
        
        .footer {
            text-align: center;
            color: white;
            margin-top: 40px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 Learning Tracker</h1>
            <p class="subtitle">Spaced Repetition System - Master Your Learning</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Active Items</h3>
                <div class="number">{{ stats.active_items }}</div>
                <div class="subtitle">Ready to learn</div>
            </div>
            <div class="stat-card">
                <h3>Mastered</h3>
                <div class="number">{{ stats.mastered_items }}</div>
                <div class="subtitle">Long-term retention</div>
            </div>
            <div class="stat-card">
                <h3>Due Now</h3>
                <div class="number">{{ stats.due_now }}</div>
                <div class="subtitle">Start reviewing →</div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div class="number">{{ (stats.average_success_rate * 100)|int }}%</div>
                <div class="subtitle">Overall average</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Quick Actions</h2>
            <a href="{{ url_for('review_session') }}" class="button">Start Review ({{ stats.due_now }} due)</a>
            <a href="{{ url_for('add_item_page') }}" class="button" style="margin-left: 10px;">Add New Item</a>
        </div>
        
        <div class="section">
            <h2>📖 Items Due Today</h2>
            {% if due_items %}
                <ul class="item-list">
                {% for item in due_items[:10] %}
                    <li class="item-card">
                        <div>
                            <div class="item-question">{{ item.question[:60] }}</div>
                            <div class="item-meta">
                                Type: <strong>{{ item.item_type }}</strong> |
                                Reviews: {{ item.total_reviews }} |
                                Success: {{ (item.success_rate * 100)|int }}%
                            </div>
                        </div>
                        <div class="item-stats">
                            <a href="{{ url_for('review_item', item_id=item.id) }}" class="button">Review</a>
                        </div>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p style="color: #666; text-align: center; padding: 40px;">
                    ✅ No items due right now. Great job! Keep up the learning.
                </p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>📚 Recent Items</h2>
            {% if recent_items %}
                <ul class="item-list">
                {% for item in recent_items[:5] %}
                    <li class="item-card">
                        <div>
                            <div class="item-question">{{ item.question[:60] }}</div>
                            <div class="item-meta">
                                Status: 
                                {% if item.status == 'mastered' %}
                                    <span class="badge badge-success">✓ Mastered</span>
                                {% elif item.total_reviews > 5 %}
                                    <span class="badge badge-info">Learning</span>
                                {% else %}
                                    <span class="badge badge-warning">New</span>
                                {% endif %}
                            </div>
                        </div>
                    </li>
                {% endfor %}
                </ul>
            {% else %}
                <p style="color: #999;">No items yet. <a href="{{ url_for('add_item_page') }}">Add your first item!</a></p>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>Learning Tracker © 2026 | Spaced Repetition System</p>
        </div>
    </div>
</body>
</html>
"""

ADD_ITEM_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Add Learning Item</title>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .form-container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #333; margin-bottom: 30px; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-family: inherit;
            font-size: 14px;
        }
        textarea { resize: vertical; min-height: 100px; }
        .buttons {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }
        button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
        }
        .btn-submit {
            background: #667eea;
            color: white;
        }
        .btn-submit:hover { background: #764ba2; }
        .btn-cancel {
            background: #6c757d;
            color: white;
        }
        .btn-cancel:hover { background: #5a6268; }
    </style>
</head>
<body>
    <div class="container">
        <div class="form-container">
            <h1>➕ Add Learning Item</h1>
            <form method="POST">
                <div class="form-group">
                    <label>Question/Prompt *</label>
                    <textarea name="question" required placeholder="What do you want to learn?"></textarea>
                </div>
                
                <div class="form-group">
                    <label>Answer/Explanation *</label>
                    <textarea name="answer" required placeholder="The answer or explanation"></textarea>
                </div>
                
                <div class="form-group">
                    <label>Difficulty</label>
                    <select name="difficulty">
                        <option value="easy">Easy (5-10 reviews)</option>
                        <option value="medium" selected>Medium (10-20 reviews)</option>
                        <option value="hard">Hard (20+ reviews)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Type</label>
                    <select name="item_type">
                        <option value="concept" selected>Concept</option>
                        <option value="definition">Definition</option>
                        <option value="formula">Formula</option>
                        <option value="procedure">Procedure</option>
                        <option value="fact">Fact</option>
                        <option value="skill">Skill</option>
                        <option value="code">Code</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Tags (comma-separated)</label>
                    <input type="text" name="tags" placeholder="python, functions, beginner">
                </div>
                
                <div class="buttons">
                    <button type="submit" class="btn-submit">✓ Add Item</button>
                    <a href="{{ url_for('index') }}" class="btn-cancel" style="display:flex;align-items:center;justify-content:center;text-decoration:none;">Cancel</a>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
"""


# Routes
@app.route('/')
def index():
    """Dashboard home"""
    stats = tracker.get_learning_stats()
    due_items = tracker.get_items_due()
    
    conn_import = __import__('sqlite3').connect(tracker.db_path)
    c = conn_import.cursor()
    c.execute('SELECT * FROM learning_items ORDER BY created_at DESC LIMIT 5')
    recent = c.fetchall()
    conn_import.close()
    
    recent_items = [tracker._row_to_dict(row) for row in recent]
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        stats=stats,
        due_items=due_items,
        recent_items=recent_items
    )


@app.route('/add', methods=['GET', 'POST'])
def add_item_page():
    """Add item page"""
    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')
        difficulty = request.form.get('difficulty', 'medium')
        item_type = request.form.get('item_type', 'concept')
        tags_str = request.form.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        
        try:
            tracker.add_learning_item(
                question=question,
                answer=answer,
                difficulty=difficulty,
                item_type=item_type,
                tags=tags
            )
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error: {e}", 400
    
    return render_template_string(ADD_ITEM_TEMPLATE)


@app.route('/review')
def review_session():
    """API for review session"""
    items = tracker.get_items_due()
    return jsonify([{
        'id': item['id'],
        'question': item['question'],
        'difficulty': item['difficulty'],
        'total_reviews': item['total_reviews']
    } for item in items])


@app.route('/review/<item_id>', methods=['GET', 'POST'])
def review_item(item_id):
    """Review single item"""
    if request.method == 'POST':
        quality = int(request.form.get('quality', 3))
        try:
            result = tracker.record_review(item_id, quality)
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error: {e}", 400
    
    item = tracker.get_item(item_id)
    return jsonify(item)


@app.route('/stats')
def stats():
    """Get statistics API"""
    stats = tracker.get_learning_stats()
    today = tracker.get_learning_today()
    return jsonify({
        'stats': stats,
        'today': today
    })


@app.route('/search')
def search():
    """Search items"""
    q = request.args.get('q', '')
    items = tracker.search_items(q)
    return jsonify([{
        'id': item['id'],
        'question': item['question'],
        'type': item['item_type'],
        'success_rate': item['success_rate'],
        'total_reviews': item['total_reviews']
    } for item in items])


def run_dashboard(debug=False, port=5000):
    """Run the Flask dashboard"""
    print(f"\n🚀 Dashboard running at: http://localhost:{port}")
    print(f"   Add items: http://localhost:{port}/add")
    print(f"   Stats API: http://localhost:{port}/stats\n")
    app.run(debug=debug, port=port)


if __name__ == "__main__":
    run_dashboard(debug=True, port=5000)
