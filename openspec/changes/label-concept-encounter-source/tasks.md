## 1. Thread source through the producer

- [x] 1.1 `tracker_app/learning/concept_scheduler.py` `add_concept`: add `source: str = "ocr"` parameter; pass it to `ConceptEncounter` (replacing the hardcoded literal)
- [x] 1.2 `tracker_app/web/api.py` `/api/v1/ingest`: pass `source="browser_extension"` when the ingest originates from the browser extension
- [x] 1.3 OCR path (activity_monitor) keeps the default `"ocr"` — no change

## 2. Regression coverage

- [x] 2.1 Test: `add_concept(source='browser_extension')` stores `source='browser_extension'`; default remains `'ocr'`
- [x] 2.2 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green
