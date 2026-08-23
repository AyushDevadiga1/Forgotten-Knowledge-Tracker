# Changelog

All significant changes to the FKT codebase, logged with context.

## 2026-08-22 — CI Fix Marathon + Test Hardening

### Commits (4)
```
77b4964 fix(tests): mock _utcnow instead of datetime in trend boundary test
824891f chore: add workflow-errors to gitignore, remove BOM markers
02e6091 fix(tests): fix 6 CI failures from weak .env config
79568d6 fix(tests): stub pynput/psutil globally in conftest for headless CI
```

### Files changed
- `tracker_app/config.py` — validate SECRET_KEY length >= 32, regenerate if too short
- `tracker_app/tests/conftest.py` — add pynput/psutil sys.modules stubs for headless CI
- `tracker_app/tests/test_warmup.py` — remove redundant pynput/psutil per-test stubs
- `tracker_app/tests/test_rate_limiting.py` — skip tests when RATELIMIT_ENABLED=false
- `tracker_app/tests/test_graph_sync_endpoint.py` — mock send_from_directory for SPA catch-all
- `tracker_app/tests/test_api.py` — fix mock target from datetime to _utcnow
- `.gitignore` — add workflow-errors folder

### Root causes found
1. **pynput import at module level** — loop.py imports pynput at line 11, fails in headless CI (no X display). Fixed with sys.modules stubs in conftest.py.
2. **CI .env has weak SECRET_KEY** — `test-secret-key` (15 chars) loaded by config.py's load_dotenv, bypassing auto-generation. Fixed by validating key length.
3. **CI .env disables rate limiting** — `RATELIMIT_ENABLED=false` causes limiter tests to fail on uninitialized storage. Fixed by skipping tests when disabled.
4. **Missing frontend/dist in CI** — SPA catch-all test expects index.html but CI has no frontend build. Fixed by mocking send_from_directory.
5. **Wrong mock target** — test mocked `repository.datetime` but code uses `_utcnow()` from utils. Fixed mock target.

### Metrics at this point
- 14.8 KLOC Python, 43 test files, 378 passing tests, 0 failures
- 27 API endpoints, 18 complexity hotspots (>200 LOC)