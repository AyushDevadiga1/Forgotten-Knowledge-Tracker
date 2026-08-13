## Context

See proposal.md — Why. Current state: both startup entry points (`web/app.py:29`, `tracking/loop.py:274`) call `init_all_databases()` = `create_all` only; `run_migrations(db_path=None)` already exists and is idempotent (registry + `schema_migrations` bookkeeping, ADD COLUMN guards, IF NOT EXISTS guards). `run_migrations` already accepts a `db_path` parameter.

## Goals / Non-Goals

**Goals:** Converge the schema at every runtime startup path; keep the runner's idempotent semantics; one database (same path the ORM engine uses).

**Non-Goals:** Rewriting migration 001-010 history; auto-migrating on unrelated tools (`tools/populate.py` etc.); transactional/backup handling (migrations are additive text/DDL operations).

## Decisions

1. Invoke `run_migrations` from `init_all_databases()` (after `init_db()`), not from each entry point. Rationale: a single choke point; `web/app.py` and `tracking/loop.py` both funnel through it. Alternative (calling in each entry point) duplicates the wiring and can be missed by future entry points.
2. Pass the resolved path explicitly. `run_migrations(db_path=<config.get_db_path()>)` so the migration connection targets the same database the ORM engine uses (per the fix-db-path-resolution-and-session-binding change; falls back to `DB_PATH` if the helper is unavailable). Alternative (no arg, frozen `DB_PATH`) risks divergence if `FKT_TEST_DB` is switched between imports.
3. Do not call `run_migrations` inside `init_db()` itself. Rationale: `init_db()` is also used by tests that build fresh schemas deliberately; keeping it create_all-only preserves that contract, while `init_all_databases()` (the "start everything" entry) gains convergence.

## Risks / Trade-offs

- [Startup latency] → `run_migrations` on an up-to-date DB is ~10 `schema_migrations` lookups; negligible.
- [Migration failure aborts startup] → `run_migrations` returns an error summary rather than raising for non-fatal cases; a failed migration does not corrupt already-applied ones (per-migration commit).
- [Fresh DB double-create] → `ensure_base_schema` runs `create_all` again; `IF NOT EXISTS`/`ADD COLUMN` guards make it a no-op.
