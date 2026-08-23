## Requirement: Flask SECRET_KEY Management

Flask SECRET_KEY MUST be cryptographically random and persisted across restarts.

### Behavior
- On first run, if `SECRET_KEY` env var is not set, generate `secrets.token_hex(32)` and save to `.env`
- loaded from env at app startup
- Never logged or exposed in error messages
- If `.env` exists but SECRET_KEY is missing, append it

### Acceptance Criteria
- [ ] First run generates random SECRET_KEY and writes to `.env`
- [ ] Subsequent runs reuse existing SECRET_KEY
- [ ] SECRET_KEY never appears in logs or error responses
