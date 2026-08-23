## Why

FKT has 3 critical security vulnerabilities (pickle RCE, no API auth, hardcoded SECRET_KEY), 3 high-severity issues (SQL injection risk, CORS wildcard, session forgery), and 7 medium-severity pipeline issues (case-sensitive concept keys, truncation data loss, race conditions, etc.). These must be fixed before any network exposure.

## What Changes

- **BREAKING**: Replace pickle serialization of knowledge graph with JSON-backed storage
- **BREAKING**: Require API key by default (generated on first run if not set)
- **BREAKING**: Generate random SECRET_KEY on first run, store in `.env`
- Fix CORS to restrict to localhost only
- Case-normalize concept keys before DB insert (lowercase)
- Add row-level locking for concurrent concept updates
- Report text truncation to caller (return flag)
- Add spaCy model check at startup with user-facing warning
- Tighten SSN regex to reduce false positives
- Remove debug print() statements from production code
- Fix inconsistent spaCy text caps (standardize to 50,000)

## Capabilities

### New Capabilities
- `security/api-auth`: API key authentication with auto-generation on first run
- `security/secret-management`: Flask SECRET_KEY auto-generation and secure storage
- `storage/knowledge-graph-json`: JSON-backed knowledge graph replacing pickle serialization

### Modified Capabilities
None - this is a security hardening change, not a behavior change.

## Impact

- `tracker_app/tracking/knowledge_graph.py`: pickle → JSON migration
- `tracker_app/web/api.py`: CORS fix, auth enforcement
- `tracker_app/config.py`: SECRET_KEY auto-generation, API key defaults
- `tracker_app/tracking/keyword_extractor.py`: text cap standardization
- `tracker_app/tracking/privacy_filter.py`: SSN regex tightening
- `tracker_app/learning/concept_scheduler.py`: case normalization, locking
- `tracker_app/tracking/ocr_module.py`: truncation reporting
- `tracker_app/tracking/audio_module.py`: remove debug prints
- `tracker_app/__init__.py`: spaCy model check at startup
