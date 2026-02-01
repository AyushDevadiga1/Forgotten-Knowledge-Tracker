"""
REST API Server for Learning Tracker
Complete API endpoints for all functionality
"""

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import json
import os
import sys

# Import core modules
from tracker_app.core.learning_tracker import LearningTracker
from tracker_app.core.advanced_analytics import AdvancedAnalytics
from tracker_app.core.notification_center import NotificationCenter
from tracker_app.core.batch_operations import BatchOperations, DataExporter, DataImporter, BackupManager
from tracker_app.config import DATA_DIR


class LearningTrackerAPI:
    """REST API for Learning Tracker"""

    def __init__(self, debug=False, port=5000):
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        self.debug = debug
        self.port = port
        
        # Initialize core systems
        self.tracker = LearningTracker()
        self.analytics = AdvancedAnalytics()
        self.notifications = NotificationCenter()
        self.batch_ops = BatchOperations()
        self.exporter = DataExporter()
        self.importer = DataImporter()
        self.backup = BackupManager()
        
        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all API routes"""
        
        # Dashboard
        @self.app.route('/', methods=['GET'])
        def index():
            return self._render_dashboard()
        
        # Items
        @self.app.route('/api/items', methods=['GET'])
        def get_items():
            """Get all items"""
            items = self.tracker.get_all_items()
            return jsonify({'items': items, 'count': len(items)})
        
        @self.app.route('/api/items', methods=['POST'])
        def create_item():
            """Create new item"""
            data = request.json
            item_id = self.tracker.add_learning_item(
                data['question'], data['answer'],
                data.get('difficulty', 'medium'),
                data.get('item_type', 'general'),
                data.get('tags', [])
            )
            return jsonify({'id': item_id, 'status': 'created'}), 201
        
        @self.app.route('/api/items/<int:item_id>', methods=['GET'])
        def get_item(item_id):
            """Get specific item"""
            # Query database
            import sqlite3
            db_path = str(DATA_DIR / 'learning_tracker.db')
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM learning_items WHERE item_id = ?', (item_id,))
                row = cursor.fetchone()
                
                if row:
                    return jsonify(dict(row))
                return jsonify({'error': 'Not found'}), 404
        
        @self.app.route('/api/items/<int:item_id>', methods=['PUT'])
        def update_item(item_id):
            """Update item"""
            data = request.json
            updates = {k: v for k, v in data.items() if k != 'item_id'}
            
            result = self.batch_ops.batch_update_items([{'item_id': item_id, **updates}])
            return jsonify({'updated': result['successful'], 'errors': result['failed']})
        
        @self.app.route('/api/items/<int:item_id>', methods=['DELETE'])
        def delete_item(item_id):
            """Delete item"""
            result = self.batch_ops.batch_delete_items([item_id])
            return jsonify({'deleted': result['deleted']})
        
        # Reviews
        @self.app.route('/api/items/due', methods=['GET'])
        def get_due_items():
            """Get items due for review"""
            items = self.tracker.get_items_due()
            return jsonify({'items': items, 'count': len(items)})
        
        @self.app.route('/api/reviews', methods=['POST'])
        def record_review():
            """Record a review"""
            data = request.json
            self.tracker.record_review(
                data['item_id'],
                data['quality_rating'],
                data.get('time_spent_seconds', 0)
            )
            return jsonify({'status': 'recorded'}), 201
        
        # Statistics
        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            """Get statistics"""
            stats = self.tracker.get_learning_stats()
            return jsonify(stats)
        
        @self.app.route('/api/analytics', methods=['GET'])
        def get_analytics():
            """Get comprehensive analytics"""
            report = self.analytics.get_comprehensive_report()
            return jsonify(report)
        
        @self.app.route('/api/analytics/retention', methods=['GET'])
        def get_retention():
            """Get retention analysis"""
            data = self.analytics.get_retention_analysis()
            return jsonify(data)
        
        @self.app.route('/api/analytics/mastery', methods=['GET'])
        def get_mastery():
            """Get mastery status"""
            data = self.analytics.get_mastery_estimate()
            return jsonify(data)
        
        @self.app.route('/api/analytics/recommendations', methods=['GET'])
        def get_recommendations():
            """Get study recommendations"""
            data = self.analytics.get_study_recommendations()
            return jsonify(data)
        
        @self.app.route('/api/analytics/trends', methods=['GET'])
        def get_trends():
            """Get performance trends"""
            data = self.analytics.get_performance_trends()
            return jsonify(data)
        
        # Search
        @self.app.route('/api/search', methods=['GET'])
        def search():
            """Search items"""
            query = request.args.get('q', '')
            results = self.tracker.search_items(query)
            return jsonify({'results': results, 'count': len(results)})
        
        # Notifications
        @self.app.route('/api/notifications', methods=['GET'])
        def get_notifications():
            """Get notifications"""
            notifs = self.notifications.get_unread_notifications()
            return jsonify({'notifications': notifs, 'count': len(notifs)})
        
        @self.app.route('/api/notifications/<int:notif_id>/read', methods=['PUT'])
        def mark_read(notif_id):
            """Mark notification as read"""
            self.notifications.mark_notification_read(notif_id)
            return jsonify({'status': 'marked_read'})
        
        # Batch Operations
        @self.app.route('/api/batch/add', methods=['POST'])
        def batch_add():
            """Batch add items"""
            data = request.json
            result = self.batch_ops.batch_add_items(data['items'])
            return jsonify(result), 201
        
        # Export
        @self.app.route('/api/export/json', methods=['GET'])
        def export_json():
            """Export to JSON"""
            include_history = request.args.get('history', 'true').lower() == 'true'
            self.exporter.export_to_json('export.json', include_history=include_history)
            return jsonify({'status': 'exported', 'file': 'export.json'})
        
        @self.app.route('/api/export/csv', methods=['GET'])
        def export_csv():
            """Export to CSV"""
            self.exporter.export_to_csv('export.csv')
            return jsonify({'status': 'exported', 'file': 'export.csv'})
        
        # Import
        @self.app.route('/api/import/json', methods=['POST'])
        def import_json():
            """Import from JSON"""
            file = request.files['file']
            result = self.importer.import_from_json(file)
            return jsonify(result), 201
        
        @self.app.route('/api/import/csv', methods=['POST'])
        def import_csv():
            """Import from CSV"""
            file = request.files['file']
            result = self.importer.import_from_csv(file)
            return jsonify(result), 201
        
        # Backup
        @self.app.route('/api/backup', methods=['POST'])
        def create_backup():
            """Create backup"""
            description = request.json.get('description', '') if request.json else ''
            backup_file = self.backup.create_backup(description)
            return jsonify({'status': 'created', 'file': backup_file}), 201
        
        @self.app.route('/api/backups', methods=['GET'])
        def list_backups():
            """List backups"""
            backups = self.backup.list_backups()
            return jsonify({'backups': backups, 'count': len(backups)})
        
        # Health check
        @self.app.route('/api/health', methods=['GET'])
        def health():
            """Health check"""
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'database': 'connected'
            })

    def _render_dashboard(self):
        """Render dashboard HTML"""
        stats = self.tracker.get_learning_stats()
        analytics = self.analytics.get_mastery_estimate()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Learning Tracker Dashboard</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       min-height: 100vh; padding: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { text-align: center; color: white; margin-bottom: 40px; }
                .header h1 { font-size: 2.5em; margin-bottom: 10px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                             gap: 20px; margin-bottom: 40px; }
                .stat-card { background: white; padding: 25px; border-radius: 10px; 
                            box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
                .stat-card h3 { color: #667eea; margin-bottom: 10px; font-size: 0.9em; }
                .stat-card .number { font-size: 2.5em; font-weight: bold; color: #333; }
                .stat-card .label { font-size: 0.85em; color: #999; margin-top: 5px; }
                .mastery-section { background: white; padding: 25px; border-radius: 10px;
                                  box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
                .mastery-section h2 { color: #667eea; margin-bottom: 20px; }
                .mastery-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                               gap: 15px; }
                .mastery-item { background: #f5f5f5; padding: 15px; border-radius: 8px; }
                .mastery-item strong { display: block; color: #667eea; }
                .mastery-item em { display: block; font-size: 0.9em; color: #666; margin-top: 5px; }
                button { background: #667eea; color: white; border: none; padding: 10px 20px;
                        border-radius: 5px; cursor: pointer; font-size: 1em; margin: 5px; }
                button:hover { background: #764ba2; }
                .button-group { text-align: center; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 Learning Tracker</h1>
                    <p>Master your knowledge with spaced repetition</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>📖 Total Items</h3>
                        <div class="number">""" + str(stats['total_items']) + """</div>
                    </div>
                    <div class="stat-card">
                        <h3>✅ Due Today</h3>
                        <div class="number">""" + str(stats['total_reviews_today']) + """</div>
                    </div>
                    <div class="stat-card">
                        <h3>📊 Total Reviews</h3>
                        <div class="number">""" + str(stats['total_reviews']) + """</div>
                    </div>
                    <div class="stat-card">
                        <h3>🔥 Current Streak</h3>
                        <div class="number">""" + str(stats.get('current_streak', 0)) + """</div>
                        <div class="label">days</div>
                    </div>
                </div>
                
                <div class="mastery-section">
                    <h2>Learning Progress</h2>
                    <div class="mastery-list">
                        <div class="mastery-item">
                            <strong>""" + str(len(analytics['mastered'])) + """</strong>
                            <em>Mastered</em>
                        </div>
                        <div class="mastery-item">
                            <strong>""" + str(len(analytics['learning'])) + """</strong>
                            <em>Learning</em>
                        </div>
                        <div class="mastery-item">
                            <strong>""" + str(len(analytics['struggling'])) + """</strong>
                            <em>Struggling</em>
                        </div>
                    </div>
                </div>
                
                <div class="button-group">
                    <button onclick="window.location.href='/api/items/due'">Start Review</button>
                    <button onclick="window.location.href='/api/stats'">View Stats</button>
                    <button onclick="window.location.href='/api/analytics'">View Analytics</button>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(html)

    def run(self):
        """Start the API server"""
        print(f"\n  🚀 Starting Learning Tracker API on http://localhost:{self.port}")
        print(f"     API Documentation: http://localhost:{self.port}/api/health")
        print(f"     Dashboard: http://localhost:{self.port}/\n")
        
        self.app.run(debug=self.debug, port=self.port, use_reloader=False)


def run_api_server(debug=False, port=5000):
    """Start API server"""
    api = LearningTrackerAPI(debug=debug, port=port)
    api.run()


if __name__ == '__main__':
    run_api_server(debug=True, port=5000)
