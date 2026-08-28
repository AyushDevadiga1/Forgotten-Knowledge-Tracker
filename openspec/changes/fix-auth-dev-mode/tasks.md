## 1. Backend auth gate fix

- [x] 1.1 In `tracker_app/web/shared.py`, update `check_api_key` to pass requests when `NO_AUTH` is truthy (`os.environ.get("NO_AUTH","false").lower() == "true"`), evaluated at request time alongside the existing empty-`API_KEY` check — matching `auth.py`'s `_NO_AUTH or not _API_KEY` semantics without removing or reordering the health/static exemption

## 2. config.py startup key handling

- [x] 2.1 In `tracker_app/config.py`, replace the `with open(_ENV_FILE, "a")` append of a generated `API_KEY` (lines 26-27) with: no key generation at all when `NO_AUTH` is truthy; otherwise generate the key in-memory only (`os.environ["API_KEY"] = secrets.token_hex(24)`), never writing to `.env`

## 3. Regression tests

- [x] 3.1 Add a test that the web API returns non-401 responses for endpoints guarded by `shared.check_api_key` when `NO_AUTH=true` and an `API_KEY` is present in the environment (mirrors `conftest.py`'s empty-key precedent but exercises the `NO_AUTH` path)
- [x] 3.2 Add a test that asserting on `_ENV_FILE` contents before/after `tracker_app.config` import shows no `API_KEY` line appended when a key is absent and `NO_AUTH=true`
- [x] 3.3 Run the existing test suite (`tracker_app/tests`) — all existing API/auth tests must still pass unmodified

## 4. Environment file hygiene (local dev)

- [ ] 4.1 In the repo `.env`, delete every accumulated `API_KEY=` line (keep `SECRET_KEY`, keep `NO_AUTH=true`); confirm the sibling `tracker_app/tests` still pass with the cleaned file present

## 5. Manual verification

- [x]5.1 Start the backend with `NO_AUTH=true`, then verify `/api/v1/stats`, `/api/v1/items`, and `/api/v1/session/status` return 200 with no `X-API-Key` header, both directly (`http://127.0.0.1:5000`) and through the Vite dev proxy (`http://localhost:5173`)
- [x]5.2 Confirm `.env` grows by zero `API_KEY` lines across the restart in 5.1
