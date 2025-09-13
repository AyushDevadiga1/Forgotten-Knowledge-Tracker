#!/usr/bin/env python3
import sys
import os

# Add the parent directory to Python path so we can import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from core.forgetting_curve import ForgettingCurve

def test_forgetting_curve():
    print("🧠 Testing Forgetting Curve Engine")
    print("==================================")
    
    curve = ForgettingCurve()
    
    # Test 1: Recent knowledge (high retention)
    recent_time = datetime.now() - timedelta(hours=2)
    retention = curve.calculate_retention(recent_time)
    print(f"1. Recent knowledge (2 hours ago): {retention:.1%} retention")
    
    # Test 2: Older knowledge (medium retention)
    older_time = datetime.now() - timedelta(days=3)
    retention = curve.calculate_retention(older_time)
    print(f"2. Older knowledge (3 days ago): {retention:.1%} retention")
    
    # Test 3: Very old knowledge (low retention)
    old_time = datetime.now() - timedelta(days=15)
    retention = curve.calculate_retention(old_time)
    print(f"3. Very old knowledge (15 days ago): {retention:.1%} retention")
    
    # Test 4: Review time calculation (4 days ago - might not need review yet)
    test_item = {
        'title': 'Python classes tutorial',
        'timestamp': (datetime.now() - timedelta(days=4)).isoformat(),
        'is_educational': True,
        'word_count': 200,
        'keywords': ['python', 'classes', 'oop', 'tutorial']
    }
    
    review_time = curve.get_next_review_time(test_item)
    if review_time:
        retention = curve.calculate_retention(datetime.now() - timedelta(days=4))
        print(f"4. Review suggested for: {test_item['title']}")
        print(f"   Retention: {retention:.1%}")
        print(f"   Review by: {review_time.strftime('%Y-%m-%d %H:%M')}")
    else:
        retention = curve.calculate_retention(datetime.now() - timedelta(days=4))
        print(f"4. No review needed yet for: {test_item['title']}")
        print(f"   Current retention: {retention:.1%} (above 30% threshold)")
    
    # Test 5: Knowledge that DEFINITELY needs review (20 days ago!)
    print("\n5. Testing knowledge that SHOULD need review:")
    very_old_item = {
        'title': 'Machine learning basics',
        'timestamp': (datetime.now() - timedelta(days=20)).isoformat(),
        'is_educational': True,
        'word_count': 50,
        'keywords': ['machine learning', 'ai', 'algorithms']
    }
    
    review_time = curve.get_next_review_time(very_old_item)
    if review_time:
        retention = curve.calculate_retention(datetime.now() - timedelta(days=20))
        print(f"   ✅ Review suggested for: {very_old_item['title']}")
        print(f"      Retention: {retention:.1%}")
        print(f"      Review by: {review_time.strftime('%Y-%m-%d')}")
        
        # Show memory strength calculation
        strength = curve.calculate_memory_strength(very_old_item)
        print(f"      Memory strength: {strength:.2f}")
    else:
        retention = curve.calculate_retention(datetime.now() - timedelta(days=20))
        print(f"   ❌ No review needed (unexpected)")
        print(f"      Retention: {retention:.1%}")
    
    print("==================================")
    print("🎉 Forgetting curve engine ready!")

if __name__ == "__main__":
    test_forgetting_curve()