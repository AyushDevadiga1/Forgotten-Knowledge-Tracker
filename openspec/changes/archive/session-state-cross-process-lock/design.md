## Context

session_state.json is a 3-field JSON file (active, started_at, stopped_at) read/written by two separate OS processes: the Flask web dashboard and the tracker loop. The current threading.Lock() is process-local and does not serialize cross-process access. The file already uses atomic tmp+replace writes, preventing corruption but not lost-update races.

## Goals / Non-Goals

**Goals:**
- Serialize cross-process reads and writes to session_state.json
- Preserve the existing atomic write pattern
- Keep the public API unchanged
- Degrade gracefully if locking infrastructure is unavailable

**Non-Goals:**
- Multi-worker WSGI deployment (not currently configured; out of scope)
- Replacing session_state.json with a different IPC mechanism (e.g., Redis, shared memory)
- Adding心跳 or lease-based locking (the file is small and operations are fast)

## Decisions

### Use the filelock library
The ilelock library (PyPI: filelock) provides a cross-platform, cross-process file-based lock. It uses msvcrt.locking on Windows and cntl.flock on Unix. It is a single-file, zero-dependency pure Python package.

**Alternatives considered:**
- cntl.flock directly: Not available on Windows.
- msvcrt.locking directly: Not available on Unix.
- PID file with stale detection: More complex, does not handle concurrent access correctly.
- multiprocessing.Lock: Requires shared memory between processes, which is not how this architecture works.

### Lock file sidecar pattern
Place a session_state.json.lock file adjacent to session_state.json. The lock is acquired for the entire read-modify-write cycle in start() and stop(), and for single reads in is_active() and get_status().

### Lock timeout
Use a short timeout (5 seconds) for lock acquisition. If the lock cannot be acquired within 5 seconds, fall back to unlocked access with a warning. This prevents deadlocks if a process crashes while holding the lock.

### Read lock vs. write lock
Use a shared (read) lock for is_active() and get_status(), and an exclusive (write) lock for start() and stop(). The filelock library supports this via FileLock (exclusive) and ReadOnlyFileLock (shared) -- but actually filelock only supports exclusive locks. Since all operations are fast (sub-millisecond file I/O), using exclusive locks for all operations is simpler and has negligible performance impact.

## Risks / Trade-offs

- **Lock contention**: If the tracker reads every 5 seconds and the web dashboard writes on user click, contention is extremely low. The lock is held for <1ms per operation. -> Mitigation: Not a practical concern.
- **Crash while holding lock**: If a process crashes mid-operation, the lock file may be held. -> Mitigation: filelock uses lockf/lock which are released by the OS when the process terminates. On Windows, msvcrt.locking locks are also released on process exit.
- **Read-only filesystem**: Lock file cannot be created. -> Mitigation: Fall back to unlocked access with a warning log.
- **New dependency**: Adds ilelock to requirements. -> Mitigation: Pure Python, zero transitive deps, ~5 KB, well-maintained (400M+ downloads/year on PyPI).
