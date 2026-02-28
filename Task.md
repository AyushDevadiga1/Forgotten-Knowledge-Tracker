FKT Master Task List
Honest reset as of 2026-02-21. Goal: make the backend actually work. CI/CD and frontend improvements are DEFERRED until backend is solid.

🔴 PHASE 1 — Fix Critical Crashes ✅ COMPLETE
The app will crash on these. Zero tolerance.

 1.1 
api.py
 calls tracker.get_connection() — this method does NOT exist on 
LearningTracker
. Will crash on every /api/v1/items GET. Fix: use sqlite3.connect(tracker.db_path) or add the method.
 1.2 
app.py
 route / opens a raw sqlite3.connect(tracker.db_path) connection but has no conn.close() in the finally block — connections are leaking on every page load.
 1.3 
api.py
 
create_item()
 calls tracker.add_learning_item(question=None, answer=None) if JSON body is missing or malformed — no null check, will store garbage or throw uncaught exception.
 1.4 
api.py
 
record_review()
: 
int(data.get('quality', 3))
 will throw TypeError if 
data
 is None (request has no JSON body). No guard.
 1.5 
tracker.py
 uses logger (line 44) before logging.basicConfig() is called (line 68). Logger is undefined at startup — will throw NameError on first load.
 1.6 
config.py
 runs DATA_DIR.mkdir(exist_ok=True) at import time — side effect on import breaks testing and causes issues in Docker/CI. Moved to 
setup_directories()
 function.
🟠 PHASE 2 — Real Tests (Automated Test Suite)
Current "tests" are not tests. 
test_all.py
 is a quick_start script. 
test_db.py
 is a data patch script.

 2.1 Create 
tests/test_sm2.py
 — unit test SM-2 algorithm

 Quality 5 increases interval correctly
 Quality < 3 resets repetitions to 0
 Ease factor never drops below MIN (1.3)
 Ease factor never exceeds MAX (2.5)
 Edge: quality exactly 0 and exactly 5
 Edge: item with 0 prior repetitions
 2.2 Create 
tests/test_learning_tracker.py
 — unit test LearningTracker using in-memory SQLite

 
add_learning_item()
 stores item and returns valid ID
 
add_learning_item()
 with empty question/answer raises ValueError (after we add validation)
 
get_items_due()
 returns only items with next_review_date <= now
 
record_review()
 updates interval, ease_factor, repetitions correctly
 
get_learning_stats()
 returns correct counts
 Edge: database with zero items
 Edge: all items mastered
 2.3 Create 
tests/test_api.py
 — Flask test client tests

 GET /api/v1/items returns 200 with correct shape
 GET /api/v1/items?status=invalid handles gracefully (not 500)
 GET /api/v1/items?limit=abc handles bad limit (not 500, crash)
 POST /api/v1/items with valid body → 201
 POST /api/v1/items with missing question → 400 (not 500)
 POST /api/v1/items with no JSON body → 400 (not 500)
 POST /api/v1/reviews with missing item_id → 400
 GET /api/v1/items/nonexistent → 404
 GET /api/v1/stats → 200 with expected keys
 2.4 Create 
tests/test_privacy_filter.py

 Credit card pattern detected and redacted
 SSN pattern detected and redacted
 Email detected and redacted
 Clean text passes through unchanged
 Empty string input doesn't crash
 2.5 Create 
tests/test_text_quality.py

 Short text (< threshold) rejected
 UI garbage text rejected
 Valid educational content accepted
 Empty string handled
 2.6 Create tests/test_config.py

 
validate_config()
 returns list (even if empty)
 Intervals are positive
 DB_PATH is a string
 2.7 Create 
run_tests.py
 — single command that runs ALL tests with coverage report

 python run_tests.py runs full suite
 Exits with code 0 if all pass, 1 if any fail
 Prints clear pass/fail summary
🟡 PHASE 3 — Software Engineering Quality
After backend works and tests pass.

 3.1 Add input validation layer to LearningTracker.add_learning_item():

Empty/None question → raise ValueError
Empty/None answer → raise ValueError
Invalid difficulty enum → raise ValueError
Question > 1000 chars → raise ValueError
 3.2 Fix 
api.py
 API endpoint issues:

limit
 param: validate it's an integer > 0 and ≤ 500 (currently crashes or allows limit=99999)
status
 param: only allow 
active
, mastered, archived, 
all
quality
 param: validate it's integer 0–5
Return proper 400 with human-readable errors (not raw exception messages)
 3.3 Fix connection leaks in 
app.py
 and 
api.py
:

Use context manager with sqlite3.connect(...) as conn: everywhere
Or use 
LearningTracker
's own methods (don't bypass the abstraction)
 3.4 Separate concerns in 
tracker.py
 (816-line God object):

Extract 
ConceptScheduler
 to its own file
Extract ActivityMonitor to its own file
tracker.py
 should only orchestrate, not contain everything
 3.5 Remove side effects from 
config.py
 on import:

Move DATA_DIR.mkdir() to an explicit 
setup()
 function called by 
main()
 3.6 Add proper structured logging (replace bare 
print()
 calls):

app.py
 uses 
print()
 for errors — should use logger.error()
db_module.py
 uses 
print()
 for errors
 3.7 Add database transactions where needed:

record_review()
 does two writes (update item + insert history) — should be one atomic transaction
🔵 PHASE 4 — ML Model Evaluation
Evaluate if models are actually doing what we think they're doing.

 4.1 Evaluate intent classifier:

What training data was it trained on?
What classes does it predict? Are they the right ones?
What's its accuracy? (need a held-out test set)
Is it better than a simple keyword matcher? (baseline comparison)
Decision: Keep custom model OR replace with simple rule-based system
 4.2 Evaluate audio classifier:

What does it classify? (speech vs music vs silence?)
Is this classification actually useful for the product?
Does it affect learning outcomes at all?
Decision: Keep OR cut it (simplify the system)
 4.3 Evaluate keyword extractor (TF-IDF):

Run it on 10 real screenshots from actual study sessions
Check if extracted keywords are actually useful concepts
Compare to manual keyword extraction
Decision: Is TF-IDF enough, or do we need KeyBERT back?
 4.4 Evaluate SM-2 implementation:

Run unit tests (Phase 2.1) to verify math is correct
Verify ease factor bounds are enforced
Verify repetitions reset correctly on failure
⚙️ PHASE 5 — DEFERRED (Do after system actually works)
 CI/CD — GitHub Actions pipeline (DEFERRED)
 Frontend redesign — Vercel-inspired UI (DEFERRED)
 Docker Compose multi-service setup (DEFERRED)
 Full SQLAlchemy ORM migration (DEFERRED)
 Monitoring / alerting (DEFERRED)
 Authentication (DEFERRED — single user app for now)
✅ Already Done (Previous Sessions)
 Privacy filter created with pre-compiled regex
 Text quality validator integrated
 Screenshot deduplication by MD5 hash
 OCR optimized to single PSM 6
 ROI detection (active window only)
 Adaptive monitoring intervals
 Import paths fixed (relative → absolute)
 CSRF protection added
 .env file for SECRET_KEY
Current priority: Phase 1 (crash fixes) → Phase 2 (tests) → can demo to anyone with confidence.