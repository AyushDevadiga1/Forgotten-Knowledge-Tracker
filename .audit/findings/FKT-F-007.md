# FKT-F-007 — ConceptEncounter.source hardcoded "ocr" for all callers, including browser ingest

- ID: FKT-F-007
- STATUS: VERIFIED
- SEVERITY: LOW
- SCOPE: tracker_app.db.models.ConceptEncounter.source contract ↔ producers
- LOCATION:
  - tracker_app/db/models.py:261 — `source = Column(String)` doc `# 'ocr' | 'browser_extension' | 'manual'`
  - tracker_app/learning/concept_scheduler.py:124-131 — `ConceptEncounter(..., source="ocr", ...)` unconditionally; called from api.py /ingest (browser extension) and loop.py
- CLAIM: The model documents an enumerated source contract, but every caller writes "ocr", so browser-extension encounters are mislabeled; any consumer filtering on source mislabels them.
- EXPECTED: source should reflect the actual acquisition channel (browser_extension for /ingest from the extension).
- OBSERVED: Live DB rows written via /ingest have context_snippet 'browser:...' while source='ocr' (code reading; contract-hunter H6).
- EVIDENCE: contract-hunter H6; concept_scheduler.py:124-131; bug-reproducer REPRODUCTION section below.
- REPRODUCTION: CONFIRMED (bug-reproducer) — see REPRODUCTION/STATUS section below.
- ROOT_CAUSE: (tentative) producer ignores documented enum; no validation.
- RELATED_PATTERN: P-007
- AFFECTED_INSTANCES: (pending)
- FIX: `ConceptScheduler.add_concept` (tracker_app/learning/concept_scheduler.py:22-28) gained `source: str = "ocr"` and passes it to `ConceptEncounter(source=source)` (replacing the hardcoded literal at :127). The `/api/v1/ingest` route (tracker_app/web/api.py:663-668) now passes `source="browser_extension"` for browser-extension ingests. OCR path (tracking/activity_monitor.py:210-215) keeps the default `"ocr"` — no change. Existing rows are not rewritten; default behavior preserved for all other callers.
- OPENSPEC_CHANGE: label-concept-encounter-source
- REGRESSION_TEST: Added `test_add_concept_stores_explicit_source` and `test_add_concept_default_source_is_ocr` in tracker_app/tests/test_concept_scheduler.py (using the existing `db` + `no_graph_sync` fixtures, in-memory SQLite). The first asserts `source='browser_extension'` is persisted when passed; the second asserts the default persists `'ocr'`.
- VERIFICATION: `venv\Scripts\python.exe -m pytest tracker_app/tests/test_concept_scheduler.py -q -k source` → 2 passed. `venv\Scripts\python.exe -m pytest tracker_app/tests -q` → 254 passed (baseline 252 + 2 new), 0 failures, only pre-existing deprecation warnings. No live DB touched; tests use throwaway in-memory DBs and monkeypatch knowledge-graph sync.
- REMAINING_RISK: low — no current consumer filters on source (grep for `source` filters in tracker_app/ returns nothing).

---

## REPRODUCTION/STATUS — bug-reproducer (2026-08-13)

### Classification
**CONFIRMED** — deterministic, reproducible contract violation. No current consumer reads the field, so blast radius is data mislabeling only, but the documented enum contract (models.py:261) is violated for the browser-ingest path.

### 1. Temp-DB probe (ConceptScheduler.add_concept with browser context)
Throwaway DB `C:\Users\hp\AppData\Local\Temp\opencode\f007_probe.db`, fresh subprocess, `FKT_TEST_DB` set before imports, `kg.sync_concept_to_graph` monkeypatched to a no-op.

Command:
```
$env:PYTHONPATH='C:\Users\hp\Desktop\FKT'; $env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f007_probe.db'; & 'C:\Users\hp\Desktop\FKT\venv\Scripts\python.exe' C:\Users\hp\AppData\Local\Temp\opencode\f007_probe.py
```
Probe body (equivalent to api.py:643-648 arguments):
```python
kg.sync_concept_to_graph = lambda concept: None
...
s.add_concept(concept="backpropagation", confidence=0.7, context="browser:New Tab - Wikipedia")
print(sqlite3.connect(DB).execute("SELECT source, context_snippet FROM concept_encounters").fetchall())
```
Output:
```
add_concept returned: backpropagation
concept_encounters rows: [('ocr', 'browser:New Tab - Wikipedia')]
```
EXPECTED per models.py:261 contract: `source='browser_extension'`. OBSERVED: `source='ocr'`.

### 2. Code evidence (writer hardcodes the value)
`tracker_app/learning/concept_scheduler.py` — the ONLY `ConceptEncounter(...)` construction in app code:
```python
124:            encounter = ConceptEncounter(
125:                concept=concept,
126:                timestamp=now,
127:                source="ocr",
128:                confidence=confidence,
129:                context_snippet=context[:200] if context else "",
130:            )
131:            db.add(encounter)
```
- Signature (lines 22-28) has no `source` parameter, so callers cannot influence it.
- `grep source=` across `tracker_app/` — exactly one hit: concept_scheduler.py:127.
- Callers: `web/api.py:643-648` (browser /ingest, passes `context=f"browser:{title[:80]}"`, `attention_at_encoding=60.0`) and `tracking/activity_monitor.py:210-215` (OCR path, passes `context="ocr"`). Both funnel into the same hardcoded construction.
- Documented enum: `tracker_app/db/models.py:261` `source = Column(String)   # 'ocr' | 'browser_extension' | 'manual'`. No code path can currently produce `'browser_extension'` or `'manual'`.

### 3. Live DB read-only corroboration (tracker_app/data/sessions.db, opened `?mode=ro`)
```
total concept_encounters: 5
browser context rows: 0
browser context + source='ocr' rows: 0
all distinct sources: [('ocr', 5)]
```
Live rows (all OCR-path; no browser rows present today): `('ocr','calvin cycle','ocr',...), ('ocr','mitochondria','ocr',...), ('ocr','photosynthesis','ocr',...), ('ocr','atp','ocr',...), ('ocr','mitochondria','',...)`.
Note: the planned "expect > 0" live query returns 0 because the current live DB contains no `browser:%` contexts. This does not refute the defect — it only means no browser ingest has persisted into this DB recently. The temp-DB and end-to-end probes below are the decisive evidence.

### 4. End-to-end probe (/api/v1/ingest — full browser route, throwaway DB)
Throwaway DB `f007_e2e.db`, fresh subprocess, `FKT_TEST_DB` before imports, `kg.sync_concept_to_graph` monkeypatched, Flask test client.
```
POST /api/v1/ingest {text: "Backpropagation is a fundamental algorithm ... gradient descent.", title: "New Tab - Wikipedia"}
-> 200 {'concepts_saved': 15, 'success': True}
```
All 15 written encounters:
```
('gradient descent', 'ocr', 'browser:New Tab - Wikipedia')
('fundamental algorithm', 'ocr', 'browser:New Tab - Wikipedia')
... (15 rows, all source='ocr', context_snippet='browser:New Tab - Wikipedia')
```
Also visible in the ORM insert log: `'source': 'ocr', 'context_snippet': 'browser:New Tab - Wikipedia'`.

### Repo hygiene
`git status --porcelain` after probes shows only pre-existing `.audit/` changes (recon.md + untracked finding/context files, fkt-audit-v3/). No `tracker_app/` files modified; `data/knowledge_graph.pkl` mtime unchanged (2026-08-12). Probes were read-only w.r.t. the repo.

### Verdict
CONFIRMED. The browser-ingest path stores `source='ocr'` for browser-sourced encounters, violating the documented `'ocr' | 'browser_extension' | 'manual'` contract. Impact is currently latent (no consumer filters on source — grep for `\.source\b|source\s*==|source\s*!=` in tracker_app/ returns nothing), matching the LOW severity.