"""
Advanced Analytics and Statistics for Learning Tracker
Provides detailed insights into learning progress, retention rates, and study patterns
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import math


class AdvancedAnalytics:
    """Comprehensive analytics for learning system"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path

    def get_retention_analysis(self) -> Dict[str, Any]:
        """Analyze retention rates across all items"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all review history
            cursor.execute('''
                SELECT li.item_id, li.question, rh.quality_rating, rh.review_date
                FROM review_history rh
                JOIN learning_items li ON rh.item_id = li.item_id
                ORDER BY rh.review_date
            ''')
            
            reviews = cursor.fetchall()
            
            # Calculate retention metrics
            total_reviews = len(reviews)
            successful_reviews = sum(1 for r in reviews if r[2] >= 3)  # quality >= 3
            success_rate = (successful_reviews / total_reviews * 100) if total_reviews > 0 else 0
            
            # Calculate by difficulty
            cursor.execute('''
                SELECT 
                    li.difficulty,
                    COUNT(rh.review_id) as total_reviews,
                    SUM(CASE WHEN rh.quality_rating >= 3 THEN 1 ELSE 0 END) as successful_reviews
                FROM review_history rh
                JOIN learning_items li ON rh.item_id = li.item_id
                GROUP BY li.difficulty
            ''')
            
            difficulty_stats = {}
            for difficulty, total, successful in cursor.fetchall():
                success_pct = (successful / total * 100) if total > 0 else 0
                difficulty_stats[difficulty] = {
                    'total_reviews': total,
                    'successful_reviews': successful,
                    'success_rate': success_pct
                }
            
            return {
                'total_reviews': total_reviews,
                'successful_reviews': successful_reviews,
                'overall_success_rate': success_rate,
                'by_difficulty': difficulty_stats
            }

    def get_learning_velocity(self, days: int = 7) -> Dict[str, Any]:
        """Calculate learning speed and progress"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Items completed in timeframe
            cursor.execute('''
                SELECT COUNT(DISTINCT item_id) as items_studied
                FROM review_history
                WHERE review_date > ?
            ''', (cutoff_date.isoformat(),))
            
            items_studied = cursor.fetchone()[0]
            
            # Average reviews per item
            cursor.execute('''
                SELECT 
                    AVG(review_count) as avg_reviews
                FROM (
                    SELECT COUNT(*) as review_count
                    FROM review_history
                    WHERE review_date > ?
                    GROUP BY item_id
                )
            ''', (cutoff_date.isoformat(),))
            
            avg_reviews = cursor.fetchone()[0] or 0
            
            # Daily average
            daily_avg = items_studied / days if days > 0 else 0
            
            return {
                'period_days': days,
                'items_studied': items_studied,
                'average_reviews_per_item': round(avg_reviews, 2),
                'daily_average': round(daily_avg, 2),
                'estimated_mastery_days': round(items_studied / daily_avg) if daily_avg > 0 else 0
            }

    def get_mastery_estimate(self) -> Dict[str, List[Dict]]:
        """Estimate which items are mastered, learning, or struggling"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all items with their current state
            cursor.execute('''
                SELECT 
                    li.item_id,
                    li.question,
                    li.easiness_factor,
                    li.repetitions,
                    MAX(rh.quality_rating) as best_quality,
                    COUNT(rh.review_id) as total_reviews,
                    AVG(rh.quality_rating) as avg_quality
                FROM learning_items li
                LEFT JOIN review_history rh ON li.item_id = rh.item_id
                GROUP BY li.item_id
                ORDER BY avg_quality DESC
            ''')
            
            mastered = []
            learning = []
            struggling = []
            
            for row in cursor.fetchall():
                item_id, question, ease, reps, best_q, total_rev, avg_q = row
                
                if total_rev is None:
                    total_rev = 0
                    avg_q = 0
                
                item_info = {
                    'item_id': item_id,
                    'question': question[:50] + '...' if len(question) > 50 else question,
                    'repetitions': reps,
                    'total_reviews': total_rev,
                    'average_quality': round(avg_q, 2) if avg_q else 0,
                    'easiness_factor': round(ease, 2)
                }
                
                # Classification logic
                if reps >= 3 and avg_q >= 4.5 and total_rev >= 5:
                    mastered.append(item_info)
                elif reps >= 2 and avg_q >= 3:
                    learning.append(item_info)
                else:
                    struggling.append(item_info)
            
            return {
                'mastered': mastered,
                'learning': learning,
                'struggling': struggling,
                'total_items': len(mastered) + len(learning) + len(struggling)
            }

    def get_study_recommendations(self) -> Dict[str, Any]:
        """Get personalized study recommendations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Items due soon
            cursor.execute('''
                SELECT 
                    item_id,
                    question,
                    next_review_date,
                    CAST((julianday(next_review_date) - julianday('now')) AS INTEGER) as days_until_due
                FROM learning_items
                WHERE next_review_date <= datetime('now', '+7 days')
                    AND next_review_date > datetime('now')
                ORDER BY next_review_date
                LIMIT 5
            ''')
            
            due_soon = [{
                'item_id': row[0],
                'question': row[1][:50] + '...' if len(row[1]) > 50 else row[1],
                'due_in_days': row[3]
            } for row in cursor.fetchall()]
            
            # Struggling items (low quality ratings)
            cursor.execute('''
                SELECT 
                    li.item_id,
                    li.question,
                    COUNT(rh.review_id) as review_count,
                    AVG(rh.quality_rating) as avg_quality
                FROM learning_items li
                LEFT JOIN review_history rh ON li.item_id = rh.item_id
                WHERE li.item_id IN (
                    SELECT item_id FROM review_history
                    WHERE review_date > datetime('now', '-7 days')
                    GROUP BY item_id
                )
                GROUP BY li.item_id
                HAVING AVG(rh.quality_rating) < 3
                ORDER BY avg_quality
                LIMIT 5
            ''')
            
            needs_attention = [{
                'item_id': row[0],
                'question': row[1][:50] + '...' if len(row[1]) > 50 else row[1],
                'recent_reviews': row[2],
                'average_quality': round(row[3], 2) if row[3] else 0
            } for row in cursor.fetchall()]
            
            return {
                'due_soon': due_soon,
                'needs_attention': needs_attention,
                'total_recommendations': len(due_soon) + len(needs_attention)
            }

    def get_time_series_data(self, days: int = 30) -> Dict[str, List]:
        """Get daily review activity for visualization"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT 
                    DATE(review_date) as review_day,
                    COUNT(*) as review_count,
                    AVG(quality_rating) as avg_quality,
                    SUM(time_spent_seconds) as total_time
                FROM review_history
                WHERE review_date > ?
                GROUP BY DATE(review_date)
                ORDER BY review_day
            ''', (cutoff_date.isoformat(),))
            
            data = {
                'dates': [],
                'review_counts': [],
                'avg_qualities': [],
                'total_times': []
            }
            
            for row in cursor.fetchall():
                data['dates'].append(row[0])
                data['review_counts'].append(row[1])
                data['avg_qualities'].append(round(row[2], 2) if row[2] else 0)
                data['total_times'].append(int(row[3]) if row[3] else 0)
            
            return data

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate complete analytics report"""
        return {
            'generated_at': datetime.now().isoformat(),
            'retention_analysis': self.get_retention_analysis(),
            'learning_velocity': self.get_learning_velocity(days=7),
            'mastery_status': self.get_mastery_estimate(),
            'recommendations': self.get_study_recommendations(),
            'time_series': self.get_time_series_data(days=30)
        }

    def get_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Weekly trend
            cursor.execute('''
                SELECT 
                    strftime('%Y-W%W', review_date) as week,
                    COUNT(*) as reviews,
                    AVG(quality_rating) as avg_quality,
                    SUM(CASE WHEN quality_rating >= 3 THEN 1 ELSE 0 END) as successful
                FROM review_history
                GROUP BY strftime('%Y-W%W', review_date)
                ORDER BY week
            ''')
            
            weekly_trends = []
            for row in cursor.fetchall():
                weekly_trends.append({
                    'period': row[0],
                    'total_reviews': row[1],
                    'average_quality': round(row[2], 2) if row[2] else 0,
                    'successful_reviews': row[3]
                })
            
            return {
                'weekly_trends': weekly_trends,
                'trend_direction': 'improving' if len(weekly_trends) > 1 and 
                                   weekly_trends[-1]['average_quality'] > weekly_trends[-2]['average_quality']
                                   else 'stable' if len(weekly_trends) > 1 else 'insufficient_data'
            }
