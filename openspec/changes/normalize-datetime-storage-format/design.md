## Context

See proposal.md — Why. Current state: raw-SQL writers use `isoformat()` ('T'); ORM reads compare space-separated text. Live DB already has 54 'T' rows in `tracked_concepts.next_review`; `sessions`, `multi_modal_logs`, `memory_decay` are ~100% 'T' (seeded). Migration runner is registry-based with `schema_migrations` bookkeeping; migrations must be idempotent and additive.

## Goals / Non-Goals

**Goals:** All DateTime-column writers use the ORM storage format (space separator); existing 'T' rows are normalized so due queries behave correctly without a fresh seed.

**Non-Goals:** Changing the ORM storage format itself; touching rows written by the ORM (space format is already correct); converting T-rows for columns not produced by raw writers.

## Decisions

1. Fix writers to produce `str(datetime)` (space separator, matches SQLAlchemy's SQLite storage format: `YYYY-MM-DD HH:MM:SS.ffffff`). Alternative (changing the ORM to read both formats) was rejected: the invariant is already documented at repository.py:270-285 and the ORM path is correct; repairing writers is the smallest fix.
2. Add migration `011_datetime_storage_format` doing text surgery: `UPDATE t SET col = substr(col,1,10) || ' ' || substr(col,12) WHERE col LIKE '____-__-__T%'` for the affected columns: `tracked_concepts` (next_review, first_seen, last_seen), `sessions` (start_ts, end_ts), `multi_modal_logs` (timestamp), `memory_decay` (last_seen_ts, updated_at). Rationale: idempotent (no 'T' rows → no-op), cannot corrupt space rows (pattern anchored at position 10), pure data repair.
3. Do not normalize `learning_items.next_review_date` (no 'T' rows today, no raw writer) — normalization is opportunistic and targeted at columns raw writers touch; the LIKE-guarded UPDATE is harmless if extended, but scope stays minimal.

## Risks / Trade-offs

- [UPDATE on large tables] → single pass over small local DBs; rowcount logged; no transaction size issue for SQLite.
- [Migration 011 vs future raw writers] → the invariant now has a migration + writer fix + the repository comment; a future 'T' writer re-triggers the bug (sibling-search noted) — mitigation: the pattern is documented in repository.py and this change's proposal.
- [Concurrent startup migration] → `run_migrations` is invoked at startup (run-migrations-at-startup change); its own connection commits per migration.
