## Purpose

Ensure that concurrent access to session_state.json from the web dashboard process and the tracker loop process is serialized via a cross-process file lock, preventing lost-update races on the shared IPC file.

## ADDED Requirements

### Requirement: Cross-process file locking
All reads and writes to session_state.json SHALL be serialized via a file-based lock that is shared across OS processes.

#### Scenario: Concurrent start from web and read from tracker
- **WHEN** the web process calls start() while the tracker process simultaneously calls is_active()
- **THEN** exactly one of them completes its file operation first, and the other sees the updated state

#### Scenario: Lock file sidecar
- **WHEN** session_state.json is accessed
- **THEN** a session_state.json.lock sidecar file is created and used for synchronization

### Requirement: Atomic write preserved
The existing write-to-temp-then-rename pattern in _save() SHALL be preserved under the file lock.

#### Scenario: Write under lock
- **WHEN** _save() acquires the file lock and writes state
- **THEN** the write uses tmp+replace and the lock is held for the entire read-modify-write cycle

### Requirement: Lock failure graceful degradation
If the file lock cannot be acquired or created (e.g., read-only filesystem), the module SHALL fall back to the current lockless behavior with a warning, rather than raising an exception.

#### Scenario: Lock file creation fails
- **WHEN** the lock file cannot be created due to filesystem permissions
- **THEN** the module logs a warning and proceeds with unlocked access

### Requirement: API compatibility
The public API of session_state.py (is_active, start, stop, get_status) SHALL remain unchanged in signature and return type.

#### Scenario: Existing callers unaffected
- **WHEN** existing code calls is_active(), start(), stop(), or get_status()
- **THEN** the return values and side effects are identical to the current implementation
