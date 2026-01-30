#!/usr/bin/env python
"""Quick validation test for critical code-level fixes"""

import sys
import os
import re

print("=" * 70)
print("🔍 CODE-LEVEL VALIDATION OF CRITICAL FIXES")
print("=" * 70)
print()

test_dir = os.path.dirname(os.path.abspath(__file__))
passed = 0
failed = 0

# Test 1: Check requirements.txt is fixed
print("Test 1: Checking requirements.txt syntax...")
req_file = os.path.join(test_dir, 'requirements.txt')
with open(req_file, 'r') as f:
    content = f.read()
    if '&&' in content or 'python -m spacy download' in content:
        print("❌ requirements.txt still has shell operators")
        failed += 1
    else:
        # Check packages are on separate lines
        lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#')]
        if 'sqlalchemy' in lines and 'cryptography' in lines and 'spacy' in lines:
            print("✅ requirements.txt is fixed - all packages on separate lines")
            passed += 1
        else:
            print("❌ requirements.txt missing expected packages")
            failed += 1

# Test 2: Check FaceDetector import removed
print("\nTest 2: Checking FaceDetector import removed...")
tracker_file = os.path.join(test_dir, 'tracker_app', 'core', 'tracker.py')
with open(tracker_file, 'r') as f:
    content = f.read()
    if 'from core.face_detection_module import FaceDetector' in content:
        print("❌ FaceDetector import still present")
        failed += 1
    else:
        print("✅ FaceDetector import removed successfully")
        passed += 1

# Test 3: Check USER_ALLOW_WEBCAM mutation fixed
print("\nTest 3: Checking USER_ALLOW_WEBCAM parameter passing...")
with open(tracker_file, 'r') as f:
    content = f.read()
    # Check for old pattern: global USER_ALLOW_WEBCAM
    if 'global USER_ALLOW_WEBCAM' in content:
        print("❌ Old global mutation pattern still present")
        failed += 1
    elif 'def ask_user_permissions():' in content and 'return allow_webcam' in content:
        # Check for new pattern: returning value
        if 'def track_loop(stop_event: Optional[Event] = None, webcam_enabled: bool' in content:
            print("✅ USER_ALLOW_WEBCAM mutation fixed - now uses parameter passing")
            passed += 1
        else:
            print("❌ track_loop signature not updated")
            failed += 1
    else:
        print("❌ ask_user_permissions function pattern not found")
        failed += 1

# Test 4: Check database context manager added
print("\nTest 4: Checking database context manager...")
db_file = os.path.join(test_dir, 'tracker_app', 'core', 'db_module.py')
with open(db_file, 'r') as f:
    content = f.read()
    if '@contextmanager' in content and 'def get_db_connection()' in content:
        print("✅ Database context manager added")
        passed += 1
    else:
        print("❌ Database context manager not found")
        failed += 1

# Test 5: Check thread safety lock added
print("\nTest 5: Checking knowledge graph thread safety lock...")
graph_file = os.path.join(test_dir, 'tracker_app', 'core', 'knowledge_graph.py')
with open(graph_file, 'r') as f:
    content = f.read()
    if '_graph_lock = threading.RLock()' in content and 'with _graph_lock:' in content:
        print("✅ Knowledge graph thread safety lock added")
        passed += 1
    else:
        print("❌ Thread safety lock not properly implemented")
        failed += 1

# Test 6: Check bare except clauses replaced in webcam_module
print("\nTest 6: Checking bare except clauses replaced...")
webcam_file = os.path.join(test_dir, 'tracker_app', 'core', 'webcam_module.py')
with open(webcam_file, 'r') as f:
    content = f.read()
    # Count bare excepts (except: with nothing after)
    bare_excepts = len(re.findall(r'except:\s*(?:#|$|\n)', content))
    if bare_excepts == 0:
        print("✅ Bare except clauses removed from webcam_module")
        passed += 1
    else:
        print(f"❌ Found {bare_excepts} bare except clauses")
        failed += 1

# Test 7: Check config validation call added
print("\nTest 7: Checking config validation called at startup...")
with open(tracker_file, 'r') as f:
    content = f.read()
    if 'validate_config()' in content and 'config_issues = validate_config()' in content:
        print("✅ Config validation is called at track_loop startup")
        passed += 1
    else:
        print("❌ Config validation not called at startup")
        failed += 1

# Test 8: Check datetime format consistency
print("\nTest 8: Checking datetime format standardization...")
memory_file = os.path.join(test_dir, 'tracker_app', 'core', 'memory_model.py')
with open(memory_file, 'r') as f:
    content = f.read()
    if 'DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"' in content:
        # Check multiple format parsing
        if content.count('datetime.fromisoformat') >= 1 and content.count('strptime') >= 2:
            print("✅ Datetime format standardized with multi-format parsing")
            passed += 1
        else:
            print("❌ Datetime parsing not properly enhanced")
            failed += 1
    else:
        print("❌ DATETIME_FORMAT constant not defined")
        failed += 1

# Test 9: Check intent label mapping improved
print("\nTest 9: Checking intent classifier label mapping fix...")
intent_file = os.path.join(test_dir, 'tracker_app', 'core', 'intent_module.py')
with open(intent_file, 'r') as f:
    content = f.read()
    if 'isinstance(intent_label_map, dict)' in content and 'inverse_transform' in content:
        print("✅ Intent label mapping handles dict and LabelEncoder types")
        passed += 1
    else:
        print("❌ Intent label mapping not properly fixed")
        failed += 1

# Test 10: Check get_db_connection usage in tracker
print("\nTest 10: Checking database context manager usage...")
with open(tracker_file, 'r') as f:
    content = f.read()
    if 'with get_db_connection() as conn:' in content:
        print("✅ Database context manager is being used in tracker")
        passed += 1
    else:
        print("❌ Database context manager not being used")
        failed += 1

print()
print("=" * 70)
print(f"CODE-LEVEL VALIDATION: {passed} passed, {failed} failed")
print("=" * 70)

if failed == 0:
    print()
    print("🎉 ALL CRITICAL FIXES VERIFIED IN CODE!")
    print()
    print("Next steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Download spaCy model: python -m spacy download en_core_web_sm")
    print("  3. Run application: python tracker_app/main.py")
    print()
else:
    print()
    print(f"❌ {failed} fix(es) need verification")
    print()

sys.exit(0 if failed == 0 else 1)
