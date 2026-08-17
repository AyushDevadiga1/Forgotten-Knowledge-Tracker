## 1. Dependency

- [x] 1.1 Add filelock to requirements.txt

## 2. Core Implementation

- [x] 2.1 Replace threading.Lock with filelock.FileLock in session_state.py
- [x] 2.2 Add lock sidecar path (_LOCK_PATH) adjacent to _STATE_PATH
- [x] 2.3 Wrap _load() and _save() callers in file lock context (exclusive lock for start/stop, exclusive for is_active/get_status)
- [x] 2.4 Add graceful degradation: catch LockTimeoutException and file creation errors, log warning, proceed unlocked

## 3. Tests

- [x] 3.1 Add test: concurrent start/stop from two processes produces consistent state
- [x] 3.2 Add test: lock file is created as sidecar next to session_state.json
- [x] 3.3 Add test: lock failure falls back to unlocked access without raising
- [x] 3.4 Verify all existing 10 session_state tests still pass

## 4. Verification

- [x] 4.1 Run full test suite (354+ tests) and confirm all pass
