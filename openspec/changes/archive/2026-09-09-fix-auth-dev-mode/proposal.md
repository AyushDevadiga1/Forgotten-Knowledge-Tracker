## Why

Local dev mode is effectively broken. The web API always returns `401 {"error":"Unauthorized"}` on every non-health endpoint when the frontend calls it without an API key, and none of the documented ways to disable auth in development work:

- `web/shared.py:check_api_key` reads `API_KEY` and returns 401 whenever it is present, but **ignores `NO_AUTH=true`** — unlike `web/auth.py`, which honors it.
- `tracker_app/config.py` **auto-generates and appends a fresh `API_KEY`** to `.env` on every boot where the key is absent, then sets it in the environment. Deleting the key from `.env` or launching with an empty `API_KEY` therefore cannot disable auth — the key comes right back each start.
- Because the key is re-appended every such boot, `.env` accumulated **110 duplicate `API_KEY` lines**, a growing footgun.

The result is an unreachable "dev mode": the redesigned frontend cannot be exercised against the real backend.

## What Changes

- `web/shared.py` gate honors `NO_AUTH=true` exactly like `web/auth.py` (single, consistent gate semantics).
- `tracker_app/config.py` no longer silently appends a regenerated `API_KEY` to `.env` on every boot when `NO_AUTH=true`; key handling for normal (auth-enabled) startup is preserved. No restart-dependent key rotation churn.
- `.env` cleanup: existing duplicate `API_KEY` lines removed so the file no longer hides stale keys.
- Regression tests added for the shared gate respecting `NO_AUTH`, mirroring the existing `API_KEY=""` precedent in `tests/conftest.py`.

## Capabilities

### New Capabilities
- `web-auth`: behavior of the web API authentication gate — when `NO_AUTH=true` disables enforcement, when `API_KEY` is required, and how a missing key is handled at startup (no silent env-file mutation).

### Modified Capabilities
<!-- None — no existing specs under openspec/specs/ -->

## Impact

- `tracker_app/config.py` — removes the unconditional append/regeneration path for dev mode.
- `tracker_app/web/shared.py` — gate honors `NO_AUTH`.
- `tracker_app/web/auth.py` — unchanged but the two gates become mutually consistent.
- All route blueprints using `shared.check_api_key` via `bp.before_request` benefit (stats, items, session, graph, quiz, intent, ingest, telemetry).
- `tracker_app/tests/*` — new regression coverage; existing tests must still pass (they already disable auth via `os.environ["API_KEY"]=""`).
- `.env` (gitignored) — historical duplicate keys removed; behavior that recreates them removed.
