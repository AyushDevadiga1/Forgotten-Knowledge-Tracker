"""
Simple Review Interface for Learning Tracker

Command-line interface for reviewing items and managing learning
"""

from core.learning_tracker import LearningTracker, DifficultyLevel
from core.sm2_memory_model import SM2Scheduler, format_next_review, format_retention_percentage
from datetime import datetime
import time


class ReviewInterface:
    """Command-line interface for reviewing learning items"""
    
    def __init__(self):
        self.tracker = LearningTracker()
        self.session_start = None
        self.session_items_reviewed = 0
    
    def run(self):
        """Main interface loop"""
        print("\n" + "="*60)
        print("📚 LEARNING TRACKER - Spaced Repetition System")
        print("="*60)
        
        while True:
            self.show_main_menu()
    
    def show_main_menu(self):
        """Main menu"""
        print("\n" + "-"*60)
        
        # Show stats
        stats = self.tracker.get_learning_stats()
        today_stats = self.tracker.get_learning_today()
        
        print(f"\n📊 STATS:")
        print(f"   Active items: {stats['active_items']} | Mastered: {stats['mastered_items']}")
        print(f"   Due now: {stats['due_now']} | Today's reviews: {today_stats['reviews_today']}")
        
        print(f"\n🎯 MENU:")
        print(f"   1. Start Review Session ({stats['due_now']} due)")
        print(f"   2. Add New Item")
        print(f"   3. Search Items")
        print(f"   4. View Statistics")
        print(f"   5. Export Items")
        print(f"   6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            self.start_review_session()
        elif choice == "2":
            self.add_new_item()
        elif choice == "3":
            self.search_items()
        elif choice == "4":
            self.view_statistics()
        elif choice == "5":
            self.export_items()
        elif choice == "6":
            print("\n✅ Goodbye! Keep learning!\n")
            exit()
        else:
            print("\n❌ Invalid option. Try again.")
    
    def start_review_session(self):
        """Review session with items due today"""
        items = self.tracker.get_items_due()
        
        if not items:
            print("\n✅ No items due for review! Great job!")
            return
        
        print(f"\n📖 Review Session: {len(items)} items due")
        print("="*60)
        
        self.session_start = datetime.now()
        self.session_items_reviewed = 0
        
        for i, item in enumerate(items, 1):
            print(f"\n[{i}/{len(items)}] Question:")
            print(f"   {item['question']}")
            print(f"\n   Difficulty: {item['difficulty']}")
            print(f"   Previous reviews: {item['total_reviews']}")
            print(f"   Success rate: {item['success_rate']:.1%}")
            
            response = self.get_review_response()
            
            if response is None:
                print("   ⏭️  Skipped")
                continue
            
            # Record review
            try:
                time_start = time.time()
                result = self.tracker.record_review(
                    item['id'],
                    quality_rating=response,
                    time_spent_seconds=int(time.time() - time_start)
                )
                self.session_items_reviewed += 1
                
                # Show feedback
                self.show_review_feedback(result)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Session summary
        self.show_session_summary(len(items))
    
    def get_review_response(self) -> int:
        """Get user's response to review item"""
        print("\n   Response (0=forgot, 1=poor, 2=weak, 3=good, 4=very good, 5=perfect, s=skip):")
        
        while True:
            response = input("   ➜ ").strip().lower()
            
            if response == "s":
                return None
            elif response in "012345":
                quality = int(response)
                
                # Show answer
                item_id = None  # We don't have it here, this is just for flow
                print(f"\n   ✓ Recorded as quality {quality}")
                return quality
            else:
                print("   ❌ Invalid input. Enter 0-5 or 's' to skip.")
    
    def show_review_feedback(self, result: dict):
        """Show feedback after recording review"""
        item = result['item']
        retention = result['retention_estimate']
        next_review = item['next_review_date']
        
        print(f"\n   ✅ Review recorded!")
        print(f"   📅 Next review: {format_next_review(datetime.fromisoformat(next_review))}")
        print(f"   📊 Predicted recall in 7 days: {format_retention_percentage(retention['7_days'])}")
        print(f"   ⭐ Ease factor: {item['ease_factor']:.2f}")
    
    def show_session_summary(self, total_items: int):
        """Show session summary"""
        if self.session_start is None:
            return
        
        duration = (datetime.now() - self.session_start).total_seconds()
        avg_per_item = duration / self.session_items_reviewed if self.session_items_reviewed > 0 else 0
        
        print("\n" + "="*60)
        print("📈 SESSION SUMMARY")
        print("="*60)
        print(f"   Items reviewed: {self.session_items_reviewed}/{total_items}")
        print(f"   Duration: {duration:.0f} seconds")
        print(f"   Avg per item: {avg_per_item:.1f} seconds")
        
        stats = self.tracker.get_learning_stats()
        print(f"\n   Overall stats:")
        print(f"   - Active items: {stats['active_items']}")
        print(f"   - Mastered: {stats['mastered_items']}")
        print(f"   - Average success: {stats['average_success_rate']:.1%}")
    
    def add_new_item(self):
        """Add new learning item"""
        print("\n" + "="*60)
        print("➕ ADD NEW ITEM")
        print("="*60)
        
        question = input("\nWhat do you want to learn? (question): ").strip()
        if not question:
            print("❌ Question required")
            return
        
        answer = input("What is the answer/explanation? ").strip()
        if not answer:
            print("❌ Answer required")
            return
        
        print("\nDifficulty:")
        print("   1. Easy (5-10 reviews)")
        print("   2. Medium (10-20 reviews)")
        print("   3. Hard (20+ reviews)")
        diff_choice = input("Select (1-3, default 2): ").strip() or "2"
        
        difficulties = {"1": "easy", "2": "medium", "3": "hard"}
        difficulty = difficulties.get(diff_choice, "medium")
        
        print("\nType of content:")
        print("   1. Concept")
        print("   2. Definition")
        print("   3. Formula")
        print("   4. Procedure")
        print("   5. Fact")
        print("   6. Skill")
        print("   7. Code")
        type_choice = input("Select (1-7, default 1): ").strip() or "1"
        
        types = {
            "1": "concept", "2": "definition", "3": "formula",
            "4": "procedure", "5": "fact", "6": "skill", "7": "code"
        }
        item_type = types.get(type_choice, "concept")
        
        tags_input = input("\nTags (comma-separated, optional): ").strip()
        tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
        
        try:
            item_id = self.tracker.add_learning_item(
                question=question,
                answer=answer,
                difficulty=difficulty,
                item_type=item_type,
                tags=tags
            )
            print(f"\n✅ Item added! ID: {item_id}")
            print("   📅 Scheduled for review now")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    def search_items(self):
        """Search for learning items"""
        query = input("\nSearch query: ").strip()
        if not query:
            return
        
        items = self.tracker.search_items(query)
        
        if not items:
            print("❌ No items found")
            return
        
        print(f"\n📚 Found {len(items)} items:\n")
        
        for item in items[:10]:
            status_icon = "✅" if item['status'] == "mastered" else "📝"
            print(f"{status_icon} {item['question'][:60]}")
            print(f"   Type: {item['item_type']} | Success: {item['success_rate']:.1%}")
            print(f"   Reviews: {item['total_reviews']} | Next: {format_next_review(datetime.fromisoformat(item['next_review_date']))}")
            print()
    
    def view_statistics(self):
        """Show detailed statistics"""
        stats = self.tracker.get_learning_stats()
        today = self.tracker.get_learning_today()
        
        print("\n" + "="*60)
        print("📊 LEARNING STATISTICS")
        print("="*60)
        
        print(f"\n📈 Overall Progress:")
        print(f"   Total items created: {stats['total_items']}")
        print(f"   Active items: {stats['active_items']}")
        print(f"   Mastered items: {stats['mastered_items']}")
        print(f"   Average success rate: {stats['average_success_rate']:.1%}")
        
        print(f"\n📅 Today:")
        print(f"   Items due: {stats['due_now']}")
        print(f"   Reviews done: {today['reviews_today']}")
        print(f"   Accuracy: {today['accuracy_today']:.1%}")
        
        print(f"\n🎯 All-time:")
        print(f"   Total reviews: {stats['total_reviews_ever']}")
        
        if stats['total_items'] > 0:
            print(f"   Avg reviews per item: {stats['total_reviews_ever'] / stats['total_items']:.1f}")
    
    def export_items(self):
        """Export learning items"""
        print("\n" + "="*60)
        print("💾 EXPORT ITEMS")
        print("="*60)
        
        print("\nFormat:")
        print("   1. JSON (for backup)")
        print("   2. Anki TSV (for importing to Anki)")
        
        choice = input("Select format (1-2): ").strip()
        
        if choice == "1":
            format_type = "json"
            filename = "learning_items.json"
        elif choice == "2":
            format_type = "anki"
            filename = "learning_items.txt"
        else:
            print("❌ Invalid choice")
            return
        
        try:
            content = self.tracker.export_items(format=format_type)
            
            with open(filename, 'w') as f:
                f.write(content)
            
            print(f"\n✅ Exported to {filename}")
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Entry point"""
    interface = ReviewInterface()
    interface.run()


if __name__ == "__main__":
    main()
