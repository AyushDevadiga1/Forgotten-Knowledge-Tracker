# ADR-001: SQLite over Client-Server SQL/NoSQL

## Status
Accepted

## Context
The Forgotten Knowledge Tracker requires a persistent data layer to log session metrics, encounters, and spaced repetition intervals. Initially, there were discussions around deploying PostgreSQL, MongoDB, or other client-server architectures to manage the `tracking_sessions` and `tracked_concepts`.

## Decision
We chose to persist strictly with Python's inbuilt `sqlite3` using multiple local `.db` files (`sessions.db`, `tracking_concepts.db`, `intent_validation.db`, `tracking_analytics.db`).

## Rationale
1. **Single-User Local First paradigm**: The tracker runs natively on a single user's OS and hooks into their local IO/Devices. There is zero multi-user collaboration overhead that would necessitate a centralized DB server.
2. **Zero Configuration**: End-users do not need to boot a docker container for Postgres/Mongo. It's a plug-and-play Python script.
3. **Low Latency**: IPC overhead of calling a remote DB is skipped. Disk IO is directly managed.

## Consequences
- **Positive**: Extremely trivial deployment footprint.
- **Negative**: No off-the-shelf cross-device synchronization. Data is tied to the physical host machine the tracker is running on.
