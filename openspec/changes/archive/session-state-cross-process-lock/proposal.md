## Why

session_state.json is the IPC bridge between the web dashboard (Flask process) and the tracker loop (separate OS process). The current threading.Lock() is process-local -- each process gets its own independent lock instance, so cross-process reads and writes are unsynchronized. This creates a race window where the tracker can capture concepts after the user clicks Stop, or the web dashboard can overwrite started_at while the tracker is mid-read.

## What Changes

- Add cross-process file locking via the filelock library to session_state.py
- Replace the process-local threading.Lock() with a file-based lock that both the web and tracker processes share
- Add filelock as a new dependency in requirements.txt
- Add regression tests that verify cross-process lock behavior (simulated via multiprocessing)

## Capabilities

### New Capabilities

- session-state-locking: Cross-process file-based locking for the shared session_state.json IPC file

### Modified Capabilities

(none -- no existing specs)

## Impact

- **Files modified**: tracker_app/tracking/session_state.py, requirements.txt
- **New dependency**: filelock (~5 KB, pure Python, no native deps)
- **Test files**: tracker_app/tests/test_session_state.py (add cross-process lock tests)
- **Behavior change**: _load() and _save() will acquire a .lock sidecar file before reading/writing, serializing access across processes
- **No API changes**: All existing is_active(), start(), stop(), get_status() signatures remain identical
- **Backward compatible**: If the lock file cannot be created (e.g., read-only filesystem), the module falls back to the current behavior with a warning
