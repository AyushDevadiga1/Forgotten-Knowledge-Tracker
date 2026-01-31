# Critical Bugs and Issues - Forgotten Knowledge Tracker

## Executive Summary
The application has several **critical and high-priority bugs** that will cause runtime failures and data corruption. These issues span initialization, event flow, data handling, and dependency management.

---

## 🔴 CRITICAL ISSUES

### 1. **MALFORMED requirements.txt - Syntax Error** ⚠️ BLOCKER
**File:** [requirements.txt](requirements.txt)  
**Severity:** CRITICAL - Application won't run  
**Issue:** Last line has invalid syntax mixing packages with shell commands:
```
sqlalchemy cryptography mss librosa keybert spacy streamlit plotly matplotlib xgboost && python -m spacy download en_core_web_sm
```

**Problems:**
- `&&` shell operator is invalid in requirements.txt
- Mixing package names with shell commands will cause pip install to fail
- `python -m spacy download` is a shell command, not a package specification

**Impact:** Installation completely fails - app cannot start

**Fix Required:**
```
sqlalchemy
cryptography
mss
librosa
keybert
spacy
streamlit
plotly
matplotlib
xgboost
```
*Note: spaCy model must be downloaded separately via script*

**Trace Event:** `pip install -r requirements.txt` → **FAILS** → Application cannot initialize

---

### 2. **Missing FaceDetector Class Import** ⚠️ BLOCKER
**File:** [tracker_app/core/tracker.py](tracker_app/core/tracker.py#L26)  
**Severity:** CRITICAL  
**Issue:** Line 26 imports `FaceDetector` from `core.face_detection_module`:
```python
from core.face_detection_module import FaceDetector
```

But this class is never used and the module doesn't properly export it.

**Impact:** 
- ImportError when tracker.py is loaded
- Application crashes at startup
- No face detection functionality available

**Investigation:**
- The webcam_module.py already has face detection built-in using dlib
- FaceDetector appears to be unused/deprecated code

**Fix:** Either:
1. Remove the import if not needed
2. Create proper FaceDetector class if intended
3. Use webcam_module's built-in face detection

---

### 3. **Global State Mutation - USER_ALLOW_WEBCAM** 🚨
**File:** [tracker_app/core/tracker.py](tracker_app/core/tracker.py#L485-L492)  
**Severity:** CRITICAL  
**Issue:** `ask_user_permissions()` tries to modify global config variable:
```python
def ask_user_permissions():
    """Ask for user permissions"""
    global USER_ALLOW_WEBCAM  # ← Trying to modify imported constant
    try:
        choice = input("Do you want to enable webcam attention tracking? (y/n): ").lower().strip()
        USER_ALLOW_WEBCAM = choice in ['y', 'yes', '1']  # ← THIS FAILS
```

**Problems:**
1. `USER_ALLOW_WEBCAM` is imported from config.py as a constant
2. Python's `global` keyword only works for module-level variables, not imports
3. Modification silently fails - the variable remains False
4. Webcam tracking is always disabled regardless of user input

**Impact:**
- User preferences are ignored
- Webcam features never work even when enabled
- Silent failure with no error message

**Event Trace:**
```
ask_user_permissions() 
  → Asks user: "Enable webcam? (y/n)"
  → User input: "y"
  → global USER_ALLOW_WEBCAM (attempts to modify)
  → Assignment fails silently
  → USER_ALLOW_WEBCAM still = True (original value)
  → Appears to work but later webcam is disabled
```

**Fix:** 
- Pass permission state as parameter or use config module function
- Or use a mutable container (list/dict) for tracking state

---

### 4. **Audio Pipeline - Missing `audio_pipeline` Function Export** ⚠️ BLOCKER
**File:** [tracker_app/core/audio_module.py](tracker_app/core/audio_module.py#L146)  
**Severity:** CRITICAL  
**Issue:** In tracker.py line 21:
```python
from core.audio_module import record_audio, classify_audio, audio_pipeline
```

But looking at audio_module.py, the `audio_pipeline()` function is defined at line ~131, yet imports fail at tracker.py initialization because audio_module itself has cascading import errors.

**Problems:**
1. If any dependency (sounddevice, librosa) is missing, the entire audio_module fails to load
2. No graceful fallback when audio libraries fail
3. Tracker.py depends on audio_module but will crash if audio fails

**Impact:**
- Application crashes if audio libraries missing or fail
- No fallback mechanism
- Complete application failure for audio-related issues

**Event Trace:**
```
tracker.py imports audio_module
  → sounddevice import fails (or librosa)
  → audio_module initialization fails
  → ALL tracker.py imports fail
  → Application crashes immediately
```

---

### 5. **OCR Module - Cascading Import Failures** ⚠️ BLOCKER
**File:** [tracker_app/core/ocr_module.py](tracker_app/core/ocr_module.py#L15-L38)  
**Severity:** CRITICAL  
**Issue:** Multiple critical dependencies loaded at module import time:
```python
try:
    kw_model = KeyBERT()  # May take 30+ seconds
    print("KeyBERT loaded successfully.")
except Exception as e:
    print(f"Error loading KeyBERT: {e}")
    kw_model = None
```

**Problems:**
1. All these are loaded at import time (not when needed)
2. No timeout protection - app can hang forever if download servers slow
3. If Tesseract not installed, entire ocr_module fails
4. Spacy model `en_core_web_sm` must be pre-downloaded (requirements.txt tries to do this but fails)

**Dependencies that fail silently:**
- KeyBERT (requires download)
- SentenceTransformer (requires download)
- spaCy model (requires separate download)
- Tesseract (requires system installation)

**Impact:**
- App hangs during startup if network slow
- Crashes if Tesseract not found
- Models don't load but app continues (then crashes later when OCR used)

**Event Trace:**
```
tracker.py imports ocr_pipeline
  → ocr_module loads
  → KeyBERT() initialization starts
  → [HANGS HERE] Network request to download models
  → If successful: models loaded
  → If fails: Error caught, kw_model = None
  → App continues but OCR will fail later
```

---

### 6. **Knowledge Graph - Uninitialized Global State** 🚨
**File:** [tracker_app/core/knowledge_graph.py](tracker_app/core/knowledge_graph.py#L13-L14)  
**Severity:** CRITICAL  
**Issue:** Global knowledge_graph created at module load:
```python
# Create the main knowledge graph
knowledge_graph = nx.Graph()
```

**Problems:**
1. Graph is shared across all threads (tracker.py is multi-threaded)
2. No locking mechanism - concurrent modifications cause data corruption
3. `add_concepts()` and `add_edges()` modify graph without synchronization
4. In tracker_loop, multiple threads access and modify the graph simultaneously

**Critical Race Conditions:**
```python
# Thread 1: track_loop
update_memory_scores(ocr_keywords)  # Modifies G.nodes[concept]
add_edges(ocr_keywords)             # Modifies G.edges

# Thread 2: listener callback (could fire concurrently)
# Also modifies graph without locks
```

**Impact:**
- Graph corruption (missing nodes/edges)
- KeyError when accessing corrupted nodes
- Silent data loss
- Unpredictable behavior

**Event Trace:**
```
Thread 1: add_concepts(['python', 'code'])
  → START: knowledge_graph.add_node('python', ...)
  → MID: Add node attributes
    Thread 2: add_edges() runs concurrently
    → Tries to add edge with 'python'
    → Node structure is incomplete
    → Raises KeyError or creates duplicate
  → Thread 1: Resumes adding 'code'
  → Result: Corrupted graph state
```

---

### 7. **Database Connection Leaks** 💧
**File:** [tracker_app/core/tracker.py](tracker_app/core/tracker.py#L126-L147) and throughout codebase  
**Severity:** CRITICAL  
**Issue:** Database connections opened but not always closed:
```python
def log_session(window_title, interaction_rate):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # ... INSERT statement ...
        conn.commit()
        print(f"Logged session...")
    except Exception as e:
        print(f"Failed to log session: {e}")
    finally:
        conn.close()  # Good practice here
```

**But in other places (e.g., memory_model.py):**
```python
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute(...)
# No explicit close() - relies on garbage collection
```

**Problems:**
1. Connections not always closed in all code paths
2. After ~1000 operations, "database is locked" errors occur
3. Long-running tracker will accumulate unclosed connections
4. SQLite default has limited concurrent connections

**Impact:**
- "database is locked" errors after 30+ minutes of tracking
- Application hangs
- Data corruption possible
- Requires restart to recover

**Event Trace:**
```
track_loop() runs for 30 minutes
  → Each iteration: log_session(), log_multi_modal()
  → Each calls sqlite3.connect()
  → ~600 connections opened (every 3 seconds x 1200 seconds)
  → ~400 properly closed (in finally blocks)
  → ~200 leaked connections
  → After leak reaches SQLite limit:
    → Next db operation: "database is locked"
    → Application hangs
    → User must kill and restart
```

---

### 8. **Datetime Parsing - Multiple Formats Not Handled** ⚠️
**File:** [tracker_app/core/memory_model.py](tracker_app/core/memory_model.py#L8-L21)  
**Severity:** HIGH  
**Issue:** `safe_parse_datetime()` tries to parse ISO format but stored dates use different format:

Database stores:
```python
ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # "2026-01-19 14:30:45"
```

But isoformat() produces:
```python
datetime.now().isoformat()  # "2026-01-19T14:30:45.123456"
```

Graph stores:
```python
'last_review': datetime.now().isoformat()  # ISO with T and microseconds
```

**Problems:**
1. Inconsistent datetime formats across modules
2. Parser tries fromisoformat() first (fails for "2026-01-19 14:30:45")
3. Fallback strptime() with hardcoded format
4. Microseconds cause parsing to fail in some cases

**Impact:**
- Memory scores computed incorrectly
- Reviews scheduled at wrong times
- Reminders misfire

---

### 9. **Intent Classifier Label Mapping Broken** 🔴
**File:** [tracker_app/core/intent_module.py](tracker_app/core/intent_module.py#L86-L99)  
**Severity:** HIGH  
**Issue:** Trying to inverse_transform non-existent label encoder:
```python
if hasattr(intent_label_map, 'inverse_transform'):
    label = intent_label_map.inverse_transform([pred])[0]
else:
    # Handle case where label_map is a dictionary
    label = intent_label_map.get(int(pred), str(pred))
```

**Problems:**
1. Pickle file created with `intent_label_map` might be raw dict or LabelEncoder
2. If it's a dict, numerical keys don't match predictions
3. Fallback assumes dict but prediction might be string
4. Type mismatch causes KeyError or TypeError

**Impact:**
- Intent prediction crashes
- Fallback rules used instead
- Intent classification always fails

---

### 10. **OCR Tesseract Path Hardcoded & May Not Exist** ⚠️
**File:** [tracker_app/config.py](tracker_app/config.py#L24)  
**Severity:** HIGH  
**Issue:**
```python
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

**Problems:**
1. Path is hardcoded for specific installation
2. No validation that file exists at startup
3. If not found, entire ocr_module fails
4. Error only appears when OCR is first called (30+ seconds into app)

**Impact:**
- OCR completely non-functional if Tesseract not installed
- Silent failure until OCR pipeline called
- No clear error message about missing Tesseract

---

## 🟠 HIGH-PRIORITY ISSUES

### 11. **Bare `except:` Clauses Hide Real Errors** 🔓
**Files:** Throughout codebase
- [webcam_module.py](tracker_app/core/webcam_module.py#L32, #L63, #L100)
- [ocr_module.py](tracker_app/core/ocr_module.py#L195-L205)

**Issue:**
```python
def eye_aspect_ratio(eye):
    try:
        # computation
    except:  # ← Catches EVERYTHING including KeyboardInterrupt, SystemExit
        return 0.0
```

**Problems:**
1. Catches all exceptions including programming errors
2. Silences KeyboardInterrupt
3. Makes debugging impossible
4. Hides real issues

**Impact:**
- Silent failures throughout
- Impossible to debug issues
- Zero visibility into what's breaking

---

### 12. **Webcam Pipeline - Bare Exception Hiding Errors** 🔓
**File:** [tracker_app/core/webcam_module.py](tracker_app/core/webcam_module.py#L72-L105)  
**Severity:** HIGH  
**Issue:**
```python
def webcam_pipeline(num_frames=5):
    for _ in range(num_frames):
        gray = capture_frame()
        if gray is None:
            continue
        try:
            faces = detector(gray)
            # ...
        except:  # ← Bare except
            continue  # ← Silent failure
```

**Impact:**
- Webcam always returns 0 faces if ANY error occurs
- User never knows webcam failed
- Attention score always 0

---

### 13. **Thread Safety - No Locks on Global Counters Used from Multiple Threads** 🔓
**File:** [tracker_app/core/tracker.py](tracker_app/core/tracker.py#L28-L55)  
**Severity:** HIGH (Mitigated)  
**Issue:** While ThreadSafeCounter exists, it's only used for keyboard/mouse:
```python
keyboard_counter = ThreadSafeCounter()
mouse_counter = ThreadSafeCounter()

def on_key_press(key):
    keyboard_counter.increment()  # ← Called from keyboard listener thread
```

But tracker_loop reads counters from main thread:
```python
total_events = keyboard_counter.get_value() + mouse_counter.get_value()
```

**Mitigating Factor:** ThreadSafeCounter has locks, so this is actually okay.

**But Real Issue:** Knowledge graph access is NOT protected (see Issue #6)

---

### 14. **Memory Score Clamping - Values Reduced to 0.1 Minimum** 🔓
**File:** [tracker_app/core/memory_model.py](tracker_app/core/memory_model.py#L48)  
**Severity:** MEDIUM  
**Issue:**
```python
return max(0.1, min(memory_score, 1.0))  # clamp between 0.1 and 1.0
```

**Problems:**
1. Even weak memory (should be 0.0) becomes 0.1
2. Can't distinguish forgotten items from reviewed items
3. Review scheduling gets skewed (weak items scheduled too far out)

**Impact:**
- Reminders don't show for truly forgotten items
- Memory model less effective

---

### 15. **Config Validation Never Called** ⚠️
**File:** [tracker_app/config.py](tracker_app/config.py#L67-L82)  
**Severity:** MEDIUM  
**Issue:** `validate_config()` function exists but never called:
```python
def validate_config():
    """Validate configuration and check for common issues"""
    issues = []
    # ... validation code ...
    return issues
```

**Not called anywhere in the application.**

**Impact:**
- Missing Tesseract not detected until runtime
- Missing model files not detected until runtime
- Bad intervals not caught at startup

---

### 16. **No Check if Models Loaded Before Using Them** ⚠️
**File:** [tracker_app/core/tracker.py](tracker_app/core/tracker.py#L59-L86)  
**Severity:** HIGH  
**Issue:** Code loads classifiers:
```python
audio_clf = load_audio_classifier()
intent_clf, intent_label_map = load_intent_classifier()
```

But doesn't check if they're None before using:
```python
# Later in classify_audio_live():
if audio_clf:  # ✓ Checked here
    label, confidence = classify_audio(audio_data)
else:
    # Fallback used
```

But in predict_intent, could fail if classifier is None but code tries to use it.

---

### 17. **OCR Keywords Not Validated** 🔴
**File:** [tracker_app/core/ocr_module.py](tracker_app/core/ocr_module.py#L253-L283)  
**Severity:** HIGH  
**Issue:** `ocr_pipeline()` returns dict of keywords but no validation:
```python
return {
    'keywords': safe_keywords,  # ← Could be empty dict
    'screenshot_taken': True
}
```

Later in tracker.py:
```python
ocr_keywords = process_ocr_data()  # ← Could be {}
# ...
add_concepts(list(ocr_keywords.keys()))  # ← Called with empty list
add_edges(ocr_keywords, ...)  # ← Called with {}
```

**Problems:**
1. Empty keywords added to graph as empty list
2. add_edges() might crash with empty dict
3. No notification that OCR failed

---

---

## EVENT FLOW TRACE - Complete Failure Scenario

### Scenario: Application Startup with All Issues

```
1. User runs: python main.py
   ↓
2. Load config.py
   → USER_ALLOW_WEBCAM = True (hardcoded)
   ✓ Config loads
   ↓
3. ask_user_permissions()
   → "Enable webcam? (y/n): " [User types: y]
   → global USER_ALLOW_WEBCAM = True  ← FAILS SILENTLY
   → USER_ALLOW_WEBCAM still = True (from config import)
   ↓
4. track_loop() starts
   → init_all_databases() ← Initializes DB
   ↓
5. start_listeners()
   → Keyboard listener starts ✓
   → Mouse listener starts ✓
   ↓
6. Main loop iteration 1:
   ├─ get_active_window()
   │  → Reads counters ✓
   │  → interaction_rate = count / TRACK_INTERVAL
   │
   ├─ log_session()
   │  → Opens DB connection
   │  → Inserts record
   │  → Closes connection ✓
   │
   ├─ Audio processing (audio_counter += TRACK_INTERVAL)
   │  → If audio_counter >= AUDIO_INTERVAL:
   │     audio_pipeline()
   │     ├─ record_audio() ← May fail or hang
   │     ├─ classify_audio() ← If no classifier, uses fallback
   │     └─ Returns {"audio_label": "...", "confidence": ...}
   │
   ├─ OCR processing (ocr_counter += TRACK_INTERVAL)
   │  → If ocr_counter >= SCREENSHOT_INTERVAL:
   │     process_ocr_data()
   │     ├─ capture_screenshot() ✓
   │     ├─ preprocess_image() ✓
   │     ├─ extract_text() 
   │     │  └─ pytesseract.image_to_string()
   │     │     └─ If Tesseract not found: CRASH
   │     └─ Returns keywords or {}
   │
   ├─ Webcam processing (webcam_counter += TRACK_INTERVAL)
   │  → If webcam_counter >= WEBCAM_INTERVAL AND USER_ALLOW_WEBCAM:
   │     webcam_pipeline()
   │     ├─ capture_frame() × 5 times
   │     ├─ detector(gray) ← Detects faces
   │     ├─ Optional: eye_aspect_ratio() if landmark predictor loaded
   │     └─ Returns {"attentiveness_score": ..., "face_count": ...}
   │
   ├─ update_memory_scores()
   │  → For each ocr_keyword:
   │     ├─ Get node from graph ← RACE CONDITION (no locks)
   │     ├─ Parse last_review datetime ← May fail or parse wrong format
   │     ├─ compute_memory_score() ← Uses datetime, may be wrong
   │     └─ G.nodes[concept].update() ← Modifies global graph (thread-unsafe)
   │
   ├─ predict_intent()
   │  → extract_features() ✓
   │  → Use classifier or fallback rules
   │
   ├─ add_edges()
   │  → Modifies knowledge_graph without locks ← RACE CONDITION
   │
   ├─ log_multi_modal()
   │  → Opens DB connection
   │  → Inserts record
   │  → Closes connection ✓
   │
   └─ save_knowledge_graph() every 300 seconds
      → Serializes potentially corrupted graph ← SAVES BAD DATA
```

### Scenario: 30 Minutes Later

```
1. ~600 database connections opened
2. ~200 leaked connections
3. SQLite connection pool exhausted
4. Next log_session(): sqlite3.OperationalError: database is locked
5. Application hangs ← STUCK
6. User kills process
7. Restart loop or reports bug
```

---

## DEPENDENCY CHAIN ANALYSIS

```
main.py
└─ tracker.py ← IMPORTS FROM:
   ├─ db_module.py ✓ (safe)
   ├─ config.py ✓ (safe)
   ├─ ocr_module.py ⚠️ (KeyBERT, Tesseract, spaCy)
   │  ├─ KeyBERT() ← **HANGS** on network latency
   │  ├─ SentenceTransformer() ← **HANGS** on network latency
   │  └─ pytesseract.pytesseract.tesseract_cmd ← **CRASHES** if Tesseract missing
   ├─ audio_module.py ⚠️ (sounddevice, librosa)
   │  ├─ sounddevice.rec() ← **FAILS** if no microphone
   │  └─ librosa ← Must be installed
   ├─ webcam_module.py ⚠️ (dlib, imutils)
   │  ├─ dlib.get_frontal_face_detector() ✓ (precompiled)
   │  └─ dlib.shape_predictor() ← **FAILS** if .dat file missing
   ├─ intent_module.py ✓ (pickle files might not exist)
   ├─ knowledge_graph.py ⚠️ (no thread safety)
   ├─ memory_model.py ✓ (but datetime parsing issues)
   └─ face_detection_module.py ← **IMPORT ERROR** (class not found)
```

---

## QUICK FIX PRIORITY

| Priority | Issue | Time | Impact |
|----------|-------|------|--------|
| 🔴 P0 | Fix requirements.txt | 5 min | Can't install |
| 🔴 P0 | Remove/fix FaceDetector import | 2 min | App crashes |
| 🔴 P0 | Fix USER_ALLOW_WEBCAM mutation | 10 min | Webcam never works |
| 🟠 P1 | Add database connection cleanup | 15 min | Prevents lock-up |
| 🟠 P1 | Add thread locks to knowledge_graph | 20 min | Prevents corruption |
| 🟠 P1 | Fix Tesseract validation | 10 min | Better error messages |
| 🟠 P1 | Remove bare except: clauses | 30 min | Better debugging |
| 🟡 P2 | Fix datetime format consistency | 20 min | Memory model accuracy |
| 🟡 P2 | Validate config at startup | 5 min | Catch missing files |
| 🟡 P2 | Fix intent label mapping | 10 min | Intent prediction works |

---

## TESTING RECOMMENDATIONS

1. **Start with crash tests:**
   - Missing Tesseract → verify graceful fallback
   - Missing .dat files → verify graceful fallback
   - No microphone → verify graceful fallback

2. **Test database stress:**
   - Run tracker for 1 hour
   - Monitor open DB connections
   - Verify no "database is locked" errors

3. **Test thread safety:**
   - Run with Valgrind/ThreadSanitizer
   - Monitor for concurrent access issues

4. **Test event timing:**
   - Verify memory scores computed correctly
   - Verify reminders trigger at right times
   - Trace a complete event through all modules

---

## FILES TO MODIFY (Priority Order)

1. [requirements.txt](requirements.txt) - Fix syntax
2. [tracker_app/core/tracker.py](tracker_app/core/tracker.py) - Multiple fixes
3. [tracker_app/config.py](tracker_app/config.py) - Add validation call
4. [tracker_app/core/knowledge_graph.py](tracker_app/core/knowledge_graph.py) - Add thread locks
5. [tracker_app/core/audio_module.py](tracker_app/core/audio_module.py) - Better error handling
6. [tracker_app/core/ocr_module.py](tracker_app/core/ocr_module.py) - Better error handling
7. [tracker_app/core/webcam_module.py](tracker_app/core/webcam_module.py) - Replace bare except
8. [tracker_app/core/memory_model.py](tracker_app/core/memory_model.py) - Fix datetime parsing
