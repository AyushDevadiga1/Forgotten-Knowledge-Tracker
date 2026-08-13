## Why

Confirmed audit finding FKT-F-007: the `ConceptEncounter.source` column documents an enum `'ocr' | 'browser_extension' | 'manual'` (models.py:261), but the only construction site — `ConceptScheduler.add_concept` (concept_scheduler.py:124-131) — hardcodes `source="ocr"` for every caller, including the browser-extension ingest route (`/api/v1/ingest`, api.py:643-648). Browser-sourced encounters are mislabeled as OCR. Reproduced end-to-end: all 15 encounters from a browser-title ingest stored `source='ocr'`. No consumer currently filters on `source`, so the impact is mislabeled telemetry today and wrong filtering logic in the future.

## What Changes

- `tracker_app/learning/concept_scheduler.py`: `add_concept` gains a `source: str = "ocr"` parameter (default preserves current behavior) and passes it to `ConceptEncounter`.
- `tracker_app/web/api.py` `/api/v1/ingest` route: passes `source="browser_extension"` for browser-extension ingests.
- `tracker_app/tracking/activity_monitor.py` OCR path: keeps the default `"ocr"` (no change needed).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`concept.encounter-source`: encounter rows record the actual acquisition channel per the model's documented enum.

## Impact

- Modified: `tracker_app/learning/concept_scheduler.py`, `tracker_app/web/api.py`
- Behavior change: new browser ingests store `source='browser_extension'`; existing rows are not rewritten.

## Notes

- Enum remains documented on the model; no schema change.
