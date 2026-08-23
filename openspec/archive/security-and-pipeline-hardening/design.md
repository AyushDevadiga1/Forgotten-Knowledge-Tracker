## Architecture

### Security Layer
```
Request → API Key Check → Route Handler
              ↓ (fail)
         401 Unauthorized
```

### Knowledge Graph Storage
```
Before:  pickle.load(pkl) → nx.Graph
After:   json.load(json) → nx.Graph (with embedding list conversion)
         Auto-migrate: pkl → json on first load
```

### Concept Key Normalization
```
Before:  "Photosynthesis" and "photosynthesis" → 2 rows
After:   concept.lower() before DB insert → 1 row
```

## Key Decisions
1. JSON over msgpack: no new dependency, human-readable, debuggable
2. Auto-generate keys: zero-config first run, secure by default
3. Lowercase normalization: simple, covers 99% of duplicates
4. Locking via SQLite WAL + SELECT FOR UPDATE pattern
