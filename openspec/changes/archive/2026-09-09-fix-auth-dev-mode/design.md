## Context

Two independent auth gates run on every `/api/v1/*` request (blueprints are registered in `web/app.py:67-71` via `apply_auth_to_blueprint`, and each route module also attaches `shared.check_api_key` as a `before_request` hook):

- `web/auth.py` ? honors `NO_AUTH=true` and an empty `API_KEY` (`if _NO_AUTH or not _API_KEY: return`).
- `web/shared.py:check_api_key` ? only honors an empty `API_KEY`; `NO_AUTH` is never consulted.

`config.py:23-28` generates a fresh `API_KEY` and **appends it to `.env`** whenever one is absent at boot, then sets it in `os.environ`. Because auth.py gate already returns `None` when `NO_AUTH=true`, but shared.py gate then 401s (observed body `{"error":"Unauthorized"}` = `shared.py:40`), dev mode is unreachable while a key exists — and every missing-key boot stacks one more `API_KEY` line into `.env` (110 duplicates found). `tests/conftest.py:31-33` sets `os.environ["API_KEY"] = ""` **after** importing config, which is why the test suite currently passes and is the established precedent for "empty effective key ? auth off".

## Goals / Non-Goals

**Goals:**
- One consistent gate semantic across both implementations: a request passes when `NO_AUTH=true` **or** the effective `API_KEY` is empty; otherwise a matching `X-API-Key` header is required.
- `config.py` SHALL NOT write `API_KEY` to the environment file at startup; dev-mode boots (`NO_AUTH=true`) neither generate nor persist a key.
- Zero behavior change for auth-enabled use with a configured `API_KEY`.

**Non-Goals:**
- No removal or unification of the two gate modules; both stay, now sharing identical pass/fail semantics (minimal blast radius, 401/403 bodies and OPTIONS handling unchanged).
- No frontend changes and no API-key distribution to the browser.
- SECRET_KEY handling is untouched.

## Decisions

**1. `shared.py:check_api_key` honors `NO_AUTH` (request-time read).**
Add `if os.environ.get("NO_AUTH", "false").lower() == "true": return None` alongside the existing empty-key check, mirroring `auth.py`'s `_NO_AUTH or not _API_KEY`. Read at request time (as this function already reads `API_KEY`) so runtime env changes and the test harness behave predictably, rather than import-time (`auth.py` reads at import; not copying that).
*Alternatives:* swap all route blueprints to `auth.py` only ? rejected: larger diff, changes health/OPTIONS/error-body behavior on 7 modules for no user-visible gain.

**2. `config.py` stops persisting a generated `API_KEY`.**
Replace the current `with open(_ENV_FILE, "a")` append with: when `API_KEY` is absent **and** `NO_AUTH` is not true, generate an **ephemeral in-process key** (`os.environ["API_KEY"] = secrets.token_hex(24)`) with no file write; when `NO_AUTH=true`, set nothing. This kills the append-storm permanently and keeps out-of-the-box auth enforcement intact, while a stable key still comes from `.env` when the operator sets one.
*Alternatives:* (a) keep appending but skip when `NO_AUTH=true` ? rejected: still accumulates in auth-enabled boot loops; (b) write the generated key to a one-time file ? rejected: more surface area than needed.

**3. `.env` hygiene (one-time, local).**
Delete the 110 stale `API_KEY` lines, leaving `SECRET_KEY` + `NO_AUTH=true`. The removal of append-behavior makes recurrence impossible.

## Risks / Trade-offs

- [Auth-enabled mode with no configured key now rotates the ephemeral key every boot] ? Mitigation: if `API_KEY` is present in `.env` it is used verbatim; ephemeral generation only fires when absent, and the startup warning text already tells operators to set `API_KEY` in `.env`.
- [Two gates still run per request] ? Mitigation: accepted cost; both now gate off identically (`NO_AUTH=true` or empty key), so no divergent outcomes.
- [Regression: API tests rely on empty `API_KEY`] ? Mitigation: `conftest.py` still clears `os.environ["API_KEY"]=""` after importing config; unchanged and verified by the existing suite.

## Migration Plan

Deploy: apply code change, clean `.env` once (Decision 3), restart backend with `NO_AUTH=true`, verify `/api/v1/stats` returns 200 directly and via the Vite proxy, then exercise the redesigned UI. Rollback: revert the commit; the append behavior returns but `.env` stays depolluted.
