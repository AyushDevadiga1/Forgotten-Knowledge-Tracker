"""
Batch Operations and Import/Export System
Handles bulk operations and data migration
"""

import sqlite3
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import os


class BatchOperations:
    """Handle batch operations on learning items"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path

    def batch_add_items(self, items: List[Dict]) -> Dict:
        """
        Add multiple items at once
        
        Args:
            items: List of dicts with 'question', 'answer', 'difficulty', 'item_type', 'tags'
        
        Returns:
            Dict with success count and any errors
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'item_ids': []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for idx, item in enumerate(items):
                try:
                    # Validate required fields
                    if not item.get('question') or not item.get('answer'):
                        raise ValueError("question and answer are required")
                    
                    cursor.execute('''
                        INSERT INTO learning_items (
                            question, answer, difficulty, item_type, tags, 
                            created_date, next_review_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item['question'],
                        item['answer'],
                        item.get('difficulty', 'medium'),
                        item.get('item_type', 'general'),
                        json.dumps(item.get('tags', [])),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    
                    results['successful'] += 1
                    results['item_ids'].append(cursor.lastrowid)
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'row': idx + 1,
                        'error': str(e)
                    })
            
            conn.commit()
        
        return results

    def batch_update_items(self, updates: List[Dict]) -> Dict:
        """
        Update multiple items at once
        
        Args:
            updates: List of dicts with 'item_id' and fields to update
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for update in updates:
                try:
                    item_id = update.pop('item_id')
                    
                    # Build update query
                    set_clause = ', '.join([f'{k} = ?' for k in update.keys()])
                    values = list(update.values()) + [item_id]
                    
                    cursor.execute(f'''
                        UPDATE learning_items
                        SET {set_clause}
                        WHERE item_id = ?
                    ''', values)
                    
                    results['successful'] += 1
                    
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'item_id': update.get('item_id'),
                        'error': str(e)
                    })
            
            conn.commit()
        
        return results

    def batch_delete_items(self, item_ids: List[int]) -> Dict:
        """Delete multiple items and their review history"""
        results = {
            'deleted': 0,
            'failed': 0
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for item_id in item_ids:
                try:
                    # Delete review history first (foreign key)
                    cursor.execute('DELETE FROM review_history WHERE item_id = ?', (item_id,))
                    
                    # Delete item
                    cursor.execute('DELETE FROM learning_items WHERE item_id = ?', (item_id,))
                    
                    results['deleted'] += 1
                    
                except Exception as e:
                    results['failed'] += 1
            
            conn.commit()
        
        return results

    def batch_tag_items(self, item_ids: List[int], tags: List[str]) -> Dict:
        """Add tags to multiple items"""
        results = {'updated': 0, 'failed': 0}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for item_id in item_ids:
                try:
                    cursor.execute('SELECT tags FROM learning_items WHERE item_id = ?', (item_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        existing_tags = json.loads(result[0]) if result[0] else []
                        updated_tags = list(set(existing_tags + tags))
                        
                        cursor.execute('''
                            UPDATE learning_items
                            SET tags = ?
                            WHERE item_id = ?
                        ''', (json.dumps(updated_tags), item_id))
                        
                        results['updated'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    results['failed'] += 1
            
            conn.commit()
        
        return results


class DataExporter:
    """Export data in various formats"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path

    def export_to_json(self, output_path: str, include_history: bool = False) -> str:
        """Export items to JSON"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT item_id, question, answer, difficulty, item_type, tags,
                       easiness_factor, repetitions, next_review_date, created_date
                FROM learning_items
                ORDER BY item_id
            ''')
            
            items = []
            for row in cursor.fetchall():
                item = {
                    'id': row[0],
                    'question': row[1],
                    'answer': row[2],
                    'difficulty': row[3],
                    'type': row[4],
                    'tags': json.loads(row[5]) if row[5] else [],
                    'easiness_factor': row[6],
                    'repetitions': row[7],
                    'next_review_date': row[8],
                    'created_date': row[9]
                }
                
                if include_history:
                    cursor.execute('''
                        SELECT quality_rating, review_date, time_spent_seconds
                        FROM review_history
                        WHERE item_id = ?
                        ORDER BY review_date
                    ''', (row[0],))
                    
                    item['review_history'] = [{
                        'quality': h[0],
                        'date': h[1],
                        'time_seconds': h[2]
                    } for h in cursor.fetchall()]
                
                items.append(item)
            
            data = {
                'export_date': datetime.now().isoformat(),
                'total_items': len(items),
                'items': items
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return output_path

    def export_to_csv(self, output_path: str) -> str:
        """Export items to CSV"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT item_id, question, answer, difficulty, item_type, tags,
                       easiness_factor, repetitions, next_review_date
                FROM learning_items
                ORDER BY item_id
            ''')
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'Question', 'Answer', 'Difficulty', 'Type', 'Tags',
                    'Easiness Factor', 'Repetitions', 'Next Review Date'
                ])
                
                for row in cursor.fetchall():
                    writer.writerow([
                        row[0], row[1], row[2], row[3], row[4],
                        ','.join(json.loads(row[5])) if row[5] else '',
                        row[6], row[7], row[8]
                    ])
            
            return output_path

    def export_to_anki(self, output_path: str) -> str:
        """Export to Anki TSV format"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT question, answer, tags FROM learning_items
                ORDER BY item_id
            ''')
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                for row in cursor.fetchall():
                    tags = ';'.join(json.loads(row[2])) if row[2] else ''
                    f.write(f"{row[0]}\t{row[1]}\t{tags}\n")
            
            return output_path


class DataImporter:
    """Import data from various formats"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path

    def import_from_json(self, file_path: str) -> Dict:
        """Import items from JSON"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        batch_op = BatchOperations(self.db_path)
        items = data.get('items', [])
        
        # Convert format
        formatted_items = []
        for item in items:
            formatted_items.append({
                'question': item['question'],
                'answer': item['answer'],
                'difficulty': item.get('difficulty', 'medium'),
                'item_type': item.get('type', 'general'),
                'tags': item.get('tags', [])
            })
        
        return batch_op.batch_add_items(formatted_items)

    def import_from_csv(self, file_path: str) -> Dict:
        """Import items from CSV"""
        items = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                items.append({
                    'question': row['Question'],
                    'answer': row['Answer'],
                    'difficulty': row.get('Difficulty', 'medium'),
                    'item_type': row.get('Type', 'general'),
                    'tags': row.get('Tags', '').split(',') if row.get('Tags') else []
                })
        
        batch_op = BatchOperations(self.db_path)
        return batch_op.batch_add_items(items)

    def import_from_anki(self, file_path: str) -> Dict:
        """Import from Anki TSV format"""
        items = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    items.append({
                        'question': parts[0],
                        'answer': parts[1],
                        'tags': parts[2].split(';') if len(parts) > 2 else [],
                        'difficulty': 'medium',
                        'item_type': 'general'
                    })
        
        batch_op = BatchOperations(self.db_path)
        return batch_op.batch_add_items(items)


class BackupManager:
    """Manage database backups and recovery"""

    def __init__(self, db_path: str = 'learning_tracker.db'):
        self.db_path = db_path
        self.backup_dir = 'backups'
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Create backup directory if it doesn't exist"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_backup(self, description: str = '') -> str:
        """Create a backup of the database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(self.backup_dir, f'backup_{timestamp}.db')
        
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_file) as target:
                source.backup(target)
        
        # Create manifest
        manifest_path = backup_file.replace('.db', '.json')
        with open(manifest_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'description': description,
                'backup_file': backup_file
            }, f)
        
        return backup_file

    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for file in os.listdir(self.backup_dir):
            if file.startswith('backup_') and file.endswith('.db'):
                manifest_file = file.replace('.db', '.json')
                manifest_path = os.path.join(self.backup_dir, manifest_file)
                
                backup_info = {
                    'file': file,
                    'path': os.path.join(self.backup_dir, file),
                    'created': os.path.getctime(os.path.join(self.backup_dir, file))
                }
                
                if os.path.exists(manifest_path):
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                        backup_info.update(manifest)
                
                backups.append(backup_info)
        
        return sorted(backups, key=lambda x: x.get('created', 0), reverse=True)

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not os.path.exists(backup_path):
            return False
        
        # Create safety backup first
        self.create_backup('pre_restore_backup')
        
        # Restore
        with sqlite3.connect(backup_path) as source:
            with sqlite3.connect(self.db_path) as target:
                source.backup(target)
        
        return True
