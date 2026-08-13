# Context pack: FKT-F-007 — ConceptEncounter.source hardcoded "ocr"

## Candidate statement (exact)
"The model documents an enumerated source contract, but every caller writes 'ocr', so browser-extension encounters are mislabeled; any consumer filtering on source mislabels them."

## Contract evidence
- models.py:261 `source = Column(String)   # 'ocr' | 'browser_extension' | 'manual'` — documented enum.
- concept_scheduler.py:124-131 — the ONLY ConceptEncounter construction site in tracker_app/, hardcodes `source="ocr"` at :127 for ALL callers.
- Callers of add_concept: web/api.py:587-656 (`/ingest`, browser extension route; passes `context=f"browser:{title[:80]}"` at :646), tracking/loop.py (OCR/screen capture — legitimately 'ocr').
- api.py:617-623 privacy gate + :625 validation = browser path is distinguishable by context, yet source is lost.

## Source locations (minimal)
- tracker_app/db/models.py:253-265 (ConceptEncounter, :261 enum doc).
- tracker_app/learning/concept_scheduler.py:110-140 (add_concept new-concept branch + :124-131 encounter row), :22-28 signature has no source param.
- tracker_app/web/api.py:587-656 (/ingest route, :646 `context=f"browser:{title[:80]}"` → add_concept at :643-648).

## Reproduction (temp DB; live DB read-only)
1. Temp DB probe: `$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f007.db'` before imports; fresh `venv\Scripts\python.exe -c`:
   - Monkeypatch `import tracker_app.tracking.knowledge_graph as kg; kg.sync_concept_to_graph = lambda c: None` (avoid writing real tracker_app/data/knowledge_graph.pkl).
   - `from tracker_app.learning.concept_scheduler import ConceptScheduler; ConceptScheduler().add_concept(concept='backpropagation', confidence=0.7, context='browser:New Tab - Wikipedia')`.
   - Read back: `SELECT source, context_snippet FROM concept_encounters` → `('ocr', 'browser:New Tab - Wikipedia')`.
   - Expected per contract: source='browser_extension' when context indicates browser ingest.
2. Live read-only: `SELECT COUNT(*) FROM concept_encounters WHERE context_snippet LIKE 'browser:%' AND source='ocr'` on tracker_app/data/sessions.db — finding reports all such rows are 'ocr'.

## Assertion points
- The single construction site passes a constant; no code path can produce 'browser_extension' or 'manual' today (grep `source=` in tracker_app/).
- context_snippet 'browser:' + source 'ocr' mismatch on live rows.

## Traps
- add_concept also runs `filter_sensitive_keywords` + `is_plausible_concept` — use a concept known to pass ('backpropagation' is used by tests/test_concept_scheduler.py:39).
- add_concept calls `sync_concept_to_graph` → writes knowledge_graph.pkl in DATA_DIR — monkeypatch it in probes to keep the repo read-only.
- Live DB: SELECT only.

## Unresolved
- Whether loop.py callers (OCR path) should pass 'ocr' explicitly and /ingest 'browser_extension'; fix = new source param + caller updates. No current consumer filters on source (remaining risk low).
