## Tasks

- [x] 1. Replace pickle with JSON in knowledge_graph.py (auto-migrate pkl→json, graceful corruption handling)
- [x] 2. Add API key auth to api.py (check X-API-Key header, exempt health/static)
- [x] 3. Auto-generate SECRET_KEY and API_KEY on first run in config.py (write to .env)
- [x] 4. Fix CORS to localhost-only in api.py
- [x] 5. Case-normalize concept keys in concept_scheduler.py (lowercase before insert)
- [x] 6. Add row-level locking for concept updates in concept_scheduler.py
- [x] 7. Return truncation flag from ocr_pipeline and browser_ingest
- [x] 8. Add spaCy model check at app startup in __init__.py
- [x] 9. Tighten SSN regex in privacy_filter.py
- [x] 10. Remove debug print() statements from production code
- [x] 11. Standardize spaCy text cap to 50,000 in ocr_module.py
- [x] 12. Run full test suite to verify no regressions
