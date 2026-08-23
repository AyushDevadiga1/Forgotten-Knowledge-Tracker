## Requirement: API Key Authentication

All API endpoints MUST require a valid API key in the `X-API-Key` header unless explicitly exempted.

### Behavior
- On first run, if `API_KEY` env var is not set, generate a random 32-byte hex string and save it to `.env`
- All `/api/v1/*` endpoints check `X-API-Key` header against the configured key
- Exempt endpoints: health check (`/api/v1/health`), static files
- Missing or invalid key returns `401 Unauthorized`
- Key is loaded once at startup; changes require restart

### Acceptance Criteria
- [ ] First run generates API key and writes to `.env`
- [ ] All non-exempt endpoints reject requests without valid key
- [ ] Exempt endpoints (health, static) work without key
- [ ] Invalid key returns 401 with JSON error body
