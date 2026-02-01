"""
Enhanced Learning Tracker - Full Featured Application
Complete command-line interface with all features
"""

import os
import sys
from datetime import datetime
from typing import Optional, List
import json

# Import core modules
from core.learning_tracker import LearningTracker
from core.sm2_memory_model import SM2Scheduler
from core.advanced_analytics import AdvancedAnalytics
from core.notification_center import NotificationCenter, RemindersSystem
from core.batch_operations import BatchOperations, DataExporter, DataImporter, BackupManager


class EnhancedReviewInterface:
    """Complete learning tracker interface"""

    def __init__(self):
        self.tracker = LearningTracker()
        self.analytics = AdvancedAnalytics()
        self.notifications = NotificationCenter()
        self.reminders = RemindersSystem()
        self.batch_ops = BatchOperations()
        self.exporter = DataExporter()
        self.importer = DataImporter()
        self.backup = BackupManager()
        self.scheduler = SM2Scheduler()

    def clear_screen(self):
        """Clear console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "="*60)
        print(f"  {text}")
        print("="*60)

    def print_section(self, text: str):
        """Print section header"""
        print(f"\n{'─'*60}")
        print(f"  {text}")
        print(f"{'─'*60}")

    def main_menu(self):
        """Main menu"""
        self.clear_screen()
        self.print_header("📚 LEARNING TRACKER - MAIN MENU")
        
        stats = self.tracker.get_learning_stats()
        today_stats = self.tracker.get_learning_today()
        print(f"\n  📊 Quick Stats:")
        print(f"     Total Items: {stats['total_items']}")
        print(f"     Due Today: {stats['due_now']}")
        print(f"     Reviewed Today: {today_stats.get('total_reviews', 0)}")
        print(f"     Current Streak: {stats.get('current_streak', 0)} days")
        
        # Check notifications
        notif_summary = self.notifications.get_notification_summary()
        if notif_summary['has_alerts']:
            print(f"\n  ⚠️  Alerts: {notif_summary['unread_notifications']} notifications")
        
        print("\n  OPTIONS:")
        print("     1. Start Review Session")
        print("     2. Add New Item")
        print("     3. Search Items")
        print("     4. View Analytics")
        print("     5. Manage Reminders & Notifications")
        print("     6. Batch Operations")
        print("     7. Import/Export Data")
        print("     8. Backup & Restore")
        print("     9. Settings")
        print("     0. Exit")
        
        choice = input("\n  Select option: ").strip()
        
        if choice == '1':
            self.start_review_session()
        elif choice == '2':
            self.add_new_item()
        elif choice == '3':
            self.search_items()
        elif choice == '4':
            self.view_analytics()
        elif choice == '5':
            self.manage_reminders()
        elif choice == '6':
            self.batch_operations_menu()
        elif choice == '7':
            self.import_export_menu()
        elif choice == '8':
            self.backup_menu()
        elif choice == '9':
            self.settings_menu()
        elif choice == '0':
            print("\n  Goodbye! Keep learning! 🚀\n")
            sys.exit(0)
        else:
            print("  Invalid option")
            input("  Press Enter to continue...")
            self.main_menu()

    def start_review_session(self):
        """Interactive review session"""
        self.clear_screen()
        self.print_header("📖 REVIEW SESSION")
        
        items = self.tracker.get_items_due()
        
        if not items:
            print("\n  ✅ No items due today! Great work!\n")
            input("  Press Enter to continue...")
            self.main_menu()
            return
        
        print(f"\n  📋 {len(items)} items due for review\n")
        
        session_stats = {'reviewed': 0, 'correct': 0, 'time_spent': 0}
        
        for idx, item in enumerate(items, 1):
            print(f"\n  [{idx}/{len(items)}]")
            print(f"  Question: {item['question']}")
            print(f"  Difficulty: {item['difficulty']}")
            
            # Show hint
            show_hint = input("\n  Show answer? (y/n): ").lower()
            
            if show_hint == 'y':
                print(f"\n  Answer: {item['answer']}")
            
            # Get quality rating
            print("\n  How well did you remember it?")
            print("     0 = No, completely forgot")
            print("     1 = No, but I remember now")
            print("     2 = Hard to recall")
            print("     3 = Good with some effort")
            print("     4 = Good, easy to recall")
            print("     5 = Perfect, instant recall")
            
            while True:
                try:
                    quality = int(input("\n  Rating (0-5): ").strip())
                    if 0 <= quality <= 5:
                        break
                    print("  Invalid rating. Please enter 0-5.")
                except ValueError:
                    print("  Invalid input. Please enter a number.")
            
            # Record review
            time_spent = 0  # Would be tracked in real app
            self.tracker.record_review(item['id'], quality, time_spent)
            session_stats['reviewed'] += 1
            if quality >= 3:
                session_stats['correct'] += 1
            
            print("  ✓ Recorded")
            
            # Ask if continue
            if idx < len(items):
                cont = input("\n  Continue? (y/n): ").lower()
                if cont != 'y':
                    break
        
        # Session summary
        self.print_section("SESSION COMPLETE")
        success_rate = (session_stats['correct'] / session_stats['reviewed'] * 100) if session_stats['reviewed'] > 0 else 0
        print(f"\n  Items Reviewed: {session_stats['reviewed']}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Great job! 🎉")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def add_new_item(self):
        """Add new learning item"""
        self.clear_screen()
        self.print_header("✏️  ADD NEW ITEM")
        
        question = input("\n  Question/Prompt: ").strip()
        if not question:
            print("  Cancelled.")
            input("  Press Enter to continue...")
            self.main_menu()
            return
        
        answer = input("  Answer: ").strip()
        if not answer:
            print("  Cancelled.")
            input("  Press Enter to continue...")
            self.main_menu()
            return
        
        print("\n  Difficulty Level:")
        print("     1. Easy")
        print("     2. Medium")
        print("     3. Hard")
        diff_choice = input("  Select (1-3): ").strip()
        difficulty_map = {'1': 'easy', '2': 'medium', '3': 'hard'}
        difficulty = difficulty_map.get(diff_choice, 'medium')
        
        item_type = input("  Type (general/vocab/formula/concept): ").strip() or 'general'
        tags_input = input("  Tags (comma-separated): ").strip()
        tags = [t.strip() for t in tags_input.split(',')] if tags_input else []
        
        item_id = self.tracker.add_learning_item(question, answer, difficulty, item_type, tags)
        
        print(f"\n  ✓ Item added! (ID: {item_id})")
        input("  Press Enter to continue...")
        self.main_menu()

    def search_items(self):
        """Search learning items"""
        self.clear_screen()
        self.print_header("🔍 SEARCH ITEMS")
        
        query = input("\n  Search query: ").strip()
        if not query:
            print("  Cancelled.")
            input("  Press Enter to continue...")
            self.main_menu()
            return
        
        results = self.tracker.search_items(query)
        
        if not results:
            print("\n  No items found.")
        else:
            print(f"\n  Found {len(results)} items:\n")
            for item in results:
                print(f"  [{item['id']}] {item['question'][:50]}")
                print(f"       Difficulty: {item['difficulty']} | Type: {item['item_type']}")
                if item.get('tags'):
                    print(f"       Tags: {', '.join(item['tags'])}")
                print()
        
        input("  Press Enter to continue...")
        self.main_menu()

    def view_analytics(self):
        """View detailed analytics"""
        self.clear_screen()
        self.print_header("📊 ANALYTICS DASHBOARD")
        
        # Retention analysis
        retention = self.analytics.get_retention_analysis()
        print(f"\n  RETENTION ANALYSIS:")
        print(f"     Total Reviews: {retention['total_reviews']}")
        print(f"     Successful: {retention['successful_reviews']}")
        print(f"     Success Rate: {retention['overall_success_rate']:.1f}%")
        
        # Learning velocity
        velocity = self.analytics.get_learning_velocity(days=7)
        print(f"\n  LEARNING VELOCITY (Last 7 days):")
        print(f"     Items Studied: {velocity['items_studied']}")
        print(f"     Daily Average: {velocity['daily_average']:.1f}")
        print(f"     Est. Mastery: {velocity['estimated_mastery_days']} days")
        
        # Mastery status
        mastery = self.analytics.get_mastery_estimate()
        print(f"\n  MASTERY STATUS:")
        print(f"     Mastered: {len(mastery['mastered'])}")
        print(f"     Learning: {len(mastery['learning'])}")
        print(f"     Struggling: {len(mastery['struggling'])}")
        
        # Recommendations
        recs = self.analytics.get_study_recommendations()
        print(f"\n  RECOMMENDATIONS:")
        print(f"     Due Soon: {len(recs['due_soon'])}")
        print(f"     Needs Attention: {len(recs['needs_attention'])}")
        
        if recs['needs_attention']:
            print(f"\n  Items Needing Attention:")
            for item in recs['needs_attention'][:5]:
                print(f"     • {item['question']}")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def manage_reminders(self):
        """Manage reminders and notifications"""
        self.clear_screen()
        self.print_header("🔔 REMINDERS & NOTIFICATIONS")
        
        reminders = self.reminders.get_active_reminders()
        print(f"\n  Active Reminders: {len(reminders)}\n")
        
        for r in reminders[:10]:
            print(f"  • {r['question']}")
            print(f"    Due: {r['time']} ({r['type']})")
        
        print("\n  OPTIONS:")
        print("     1. Create Reminder")
        print("     2. View Notifications")
        print("     3. Clear Read Notifications")
        print("     0. Back")
        
        choice = input("\n  Select: ").strip()
        
        if choice == '1':
            item_id = input("  Item ID: ").strip()
            try:
                self.reminders.create_reminder(int(item_id))
                print("  ✓ Reminder created!")
            except Exception as e:
                print(f"  Error: {e}")
        
        elif choice == '2':
            notifs = self.notifications.get_unread_notifications()
            print(f"\n  Notifications: {len(notifs)}")
            for n in notifs:
                print(f"  • {n['title']}: {n['message']}")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def batch_operations_menu(self):
        """Batch operations menu"""
        self.clear_screen()
        self.print_header("📦 BATCH OPERATIONS")
        
        print("\n  OPTIONS:")
        print("     1. Batch Add Items")
        print("     2. Batch Update Items")
        print("     3. Batch Delete Items")
        print("     4. Add Tags to Multiple Items")
        print("     0. Back")
        
        choice = input("\n  Select: ").strip()
        
        if choice == '1':
            self._batch_add_items()
        elif choice == '2':
            print("  This feature requires a CSV file with updates.")
        elif choice == '3':
            item_ids_str = input("  Item IDs (comma-separated): ").strip()
            try:
                ids = [int(i.strip()) for i in item_ids_str.split(',')]
                result = self.batch_ops.batch_delete_items(ids)
                print(f"  ✓ Deleted {result['deleted']} items")
            except Exception as e:
                print(f"  Error: {e}")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def _batch_add_items(self):
        """Batch add items"""
        csv_file = input("  CSV file path (Question,Answer,Difficulty,Type,Tags): ").strip()
        
        if not os.path.exists(csv_file):
            print("  File not found.")
            return
        
        try:
            result = self.importer.import_from_csv(csv_file)
            print(f"\n  ✓ Imported {result['successful']} items")
            if result['failed'] > 0:
                print(f"  ⚠️  {result['failed']} items failed")
                for error in result['errors'][:5]:
                    print(f"     Row {error['row']}: {error['error']}")
        except Exception as e:
            print(f"  Error: {e}")

    def import_export_menu(self):
        """Import/Export menu"""
        self.clear_screen()
        self.print_header("📤 IMPORT/EXPORT")
        
        print("\n  OPTIONS:")
        print("     1. Export to JSON")
        print("     2. Export to CSV")
        print("     3. Export to Anki")
        print("     4. Import from JSON")
        print("     5. Import from CSV")
        print("     6. Import from Anki")
        print("     0. Back")
        
        choice = input("\n  Select: ").strip()
        
        if choice == '1':
            output = self.exporter.export_to_json('export.json', include_history=True)
            print(f"  ✓ Exported to {output}")
        elif choice == '2':
            output = self.exporter.export_to_csv('export.csv')
            print(f"  ✓ Exported to {output}")
        elif choice == '3':
            output = self.exporter.export_to_anki('export.txt')
            print(f"  ✓ Exported to {output}")
        elif choice == '4':
            file_path = input("  JSON file path: ").strip()
            result = self.importer.import_from_json(file_path)
            print(f"  ✓ Imported {result['successful']} items")
        elif choice == '5':
            file_path = input("  CSV file path: ").strip()
            result = self.importer.import_from_csv(file_path)
            print(f"  ✓ Imported {result['successful']} items")
        elif choice == '6':
            file_path = input("  Anki file path: ").strip()
            result = self.importer.import_from_anki(file_path)
            print(f"  ✓ Imported {result['successful']} items")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def backup_menu(self):
        """Backup and restore menu"""
        self.clear_screen()
        self.print_header("💾 BACKUP & RESTORE")
        
        print("\n  OPTIONS:")
        print("     1. Create Backup")
        print("     2. List Backups")
        print("     3. Restore from Backup")
        print("     0. Back")
        
        choice = input("\n  Select: ").strip()
        
        if choice == '1':
            desc = input("  Description: ").strip()
            backup_file = self.backup.create_backup(desc)
            print(f"  ✓ Backup created: {backup_file}")
        
        elif choice == '2':
            backups = self.backup.list_backups()
            print(f"\n  Found {len(backups)} backups:\n")
            for idx, b in enumerate(backups, 1):
                print(f"  {idx}. {b['file']}")
                if b.get('description'):
                    print(f"     {b['description']}")
        
        elif choice == '3':
            backups = self.backup.list_backups()
            if not backups:
                print("  No backups available.")
            else:
                for idx, b in enumerate(backups, 1):
                    print(f"  {idx}. {b['file']}")
                
                choice = input("\n  Select backup number: ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(backups):
                        if self.backup.restore_from_backup(backups[idx]['path']):
                            print("  ✓ Restored successfully!")
                        else:
                            print("  Error restoring backup.")
                except ValueError:
                    print("  Invalid selection.")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def settings_menu(self):
        """Settings menu"""
        self.clear_screen()
        self.print_header("⚙️  SETTINGS")
        
        print("\n  OPTIONS:")
        print("     1. Review Daily Goal")
        print("     2. Notification Preferences")
        print("     3. Database Info")
        print("     0. Back")
        
        choice = input("\n  Select: ").strip()
        
        if choice == '3':
            stats = self.tracker.get_learning_stats()
            print(f"\n  DATABASE INFO:")
            print(f"     Total Items: {stats['total_items']}")
            print(f"     Total Reviews: {stats['total_reviews']}")
            print(f"     Database Size: ~{os.path.getsize('learning_tracker.db') / 1024:.1f} KB")
        
        input("\n  Press Enter to continue...")
        self.main_menu()

    def run(self):
        """Start the application"""
        try:
            self.main_menu()
        except KeyboardInterrupt:
            print("\n\n  Interrupted. Goodbye!\n")
            sys.exit(0)
        except Exception as e:
            print(f"\n  Error: {e}\n")
            input("  Press Enter to continue...")
            self.run()


def main():
    """Main entry point"""
    app = EnhancedReviewInterface()
    app.run()


if __name__ == '__main__':
    main()
