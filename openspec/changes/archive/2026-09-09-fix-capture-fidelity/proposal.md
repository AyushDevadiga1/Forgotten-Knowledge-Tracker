## Why

The tracking/learning pipeline discards all real study content at the ingest boundary: OCR body text and browser-selected text are reduced to bare keywords and then thrown away, so the deck answers are placeholders, the knowledge graph is degenerate, the micro-quiz cannot test knowledge, and telemetry has no runtime writers. The system is structurally "garbage in, garbage out" (evidence in `workflow-errors/current-problems.md`, P1-P8), regardless of sensor quality.

## What Changes

- **Persist real capture context (P1).** OCR `raw_text` (up to 500 chars) and the browser selection text feed `ConceptEncounter.context_snippet` instead of the literal `"ocr"` / `"browser:<title>"`.
- **Derive deck answers from content (P2).** `concept_promotion._answer_for` builds answers from persisted content; concepts with no real content cannot auto-promote.
- **Quiz honesty (P3).** Micro-quiz only serves concepts that have persisted content; the question text reflects real context instead of a bare keyword self-report.
- **Graph edges from co-occurrence (P4).** Semantic-only edges are supplemented/limited by co-occurrence within the same capture window so the graph is not near-empty junk; keep it honest but sparse.
- **Telemetry writers (P5).** The tracking loop writes real `multi_modal_logs` rows (and `metrics`) so the telemetry dashboard shows actual capture, not seed data or empty series.
- **Review-feedback path verified (P6).** The `record_review` → history → λ-recalibration chain is exercised end-to-end so personalization feedback has a proven, tested path (no silent dead-ends).
- **Seed isolation (P7).** `tools/populate.py` refuses to run into the real DB unless explicitly enabled; seeds are untracked demo data that can no longer be mistaken for real usage.
- **Deck noise reduction (P8).** Near-duplicate and fragment single-word concepts (`atp` dup, `cells convert`, ...) are excluded at promotion/backfill.

## Capabilities

### New Capabilities
- `capture-fidelity`: end-to-end fidelity of captured study content — how OCR/browser text is persisted, how deck answers and quiz questions are derived, how graph edges form, and how telemetry rows are produced from real captures.

### Modified Capabilities
None — no `openspec/specs/` main specs exist yet; all previous changes defined delta specs under their change dirs.

## Impact

- `tracker_app/tracking/loop.py`, `tracking/activity_monitor.py`, `tracking/ocr_module.py` — pass/persist raw text.
- `tracker_app/web/routes/ingest.py` — persist cleaned selection text as context.
- `tracker_app/learning/concept_promotion.py`, `learning/concept_scheduler.py` — content gating + answer derivation.
- `tracker_app/tracking/quiz_engine.py` — content-backed questions.
- `tracker_app/tracking/knowledge_graph.py` — co-occurrence edges.
- `tracker_app/db/repository.py` — telemetry writers.
- `tracker_app/tools/populate.py` — seed guard.
- New regression tests in `tracker_app/tests/`.
