## Requirement: JSON-backed Knowledge Graph

Knowledge graph MUST use JSON serialization instead of pickle for security and portability.

### Behavior
- Graph stored as `DATA_DIR/knowledge_graph.json` (replacing `.pkl`)
- On startup, if `.json` doesn't exist but `.pkl` does, migrate automatically
- Node attributes stored as JSON-serializable types (lists, dicts, strings, numbers)
- Embeddings stored as lists of floats (not numpy arrays)
- Max nodes: 5,000 (unchanged)
- Graceful degradation: if JSON is corrupted, start with empty graph and log warning

### Acceptance Criteria
- [ ] Graph saves as JSON, loads from JSON
- [ ] Automatic migration from pickle on first run
- [ ] Corrupted JSON results in empty graph + warning (not crash)
- [ ] All existing graph operations work identically
