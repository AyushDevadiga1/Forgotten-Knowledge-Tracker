## 1. Persist capture content (spec: Persist real capture content as encounter context)

- [x] 1.1 In `tracker_app/tracking/ocr_module.py`, sanitize `raw_text` before returning from `capture_ocr` (`sanitize_text_for_storage` -> drop when not `safe_to_store` -> `strip_redaction_markers`, existing 500-char cap)
- [x] 1.2 In `tracker_app/tracking/loop.py`, pass `context_text=ocr_result["raw_text"][:CONTEXT_MAX_LENGTH]` into `process_concepts` instead of the literal `ocr`
- [x] 1.3 In `tracker_app/tracking/activity_monitor.py`, thread the sanitized text through `process_concepts(...)` -> `concept_scheduler.add_concept(...)` so the excerpt lands in `ConceptEncounter.context_snippet`; drop sensitive/redacted text to empty
- [x] 1.4 In `tracker_app/web/routes/ingest.py`, persist `validation["cleaned_text"][:CONTEXT_MAX_LENGTH]` as context instead of `f"browser:{title}"`; nothing persisted when text fails the existing gates

## 2. Content-gated deck answers (spec: Deck answers are derived from real content)

- [x] 2.1 Replace `_answer_for` in `tracker_app/learning/concept_promotion.py`: return `None` unless newest context snippet is real (`len > 8`, not `ocr`, prefix-stripped); remove the template placeholder string
- [x] 2.2 Make `promote_concept_to_deck` (and `backfill_items`) skip promotion when the answer is `None`, logging instead of creating a placeholder deck item

## 3. Content-backed micro-quiz (spec: Micro-quiz questions are content-backed)

- [x] 3.1 In `tracker_app/tracking/quiz_engine.py`, build the MC candidate pool from concepts whose latest encounter has a real excerpt (group `ConceptEncounter` by concept, `len > 8`, not `ocr`)
- [x] 3.2 Change the MC stem to reference captured material (`"Which of these concepts does this captured material cover?"` with the excerpt), and return `None` when the pool is empty

## 4. Co-occurrence graph edges (spec: Graph edges reflect co-occurrence within capture windows)

- [x] 4.1 Add `record_capture_window(concepts)` in `tracker_app/tracking/knowledge_graph.py`: increment pair counters per window, cap 30 pairs/window, edge weight based on count, `reason="cooccur"`
- [x] 4.2 Call `record_capture_window` from `loop.py` and `ingest.py` with each capture window's keyword set; existing embedding edges unchanged

## 5. Runtime telemetry writers (spec: Telemetry is written by the runtime tracker)

- [x] 5.1 Add `TrackingRepository.log_multimodal(...)` inserting a `MultiModalLog` row (window title, keywords JSON, audio label, attention, interaction rate, intent, confidence, memory_score)
- [x] 5.2 Call `log_multimodal` from the tracking loop once per capture cycle while a session is active
- [x] 5.3 Persist `Metric` rows (per session concept, AWFC memory score) at session end in the tracking session path, so metrics come from real sessions
- [x] 5.4 Add a test that telemetry summary counts runtime-written rows within the 24h window

## 6. Seed guard and marker (spec: Seed data cannot be mistaken for real data)

- [x] 6.1 In `tools/populate.py`, abort with message and write nothing unless `FKT_SEED=1` env var is set
- [x] 6.2 When enabled, mark the run by writing a `Metric` row (`concept="__seed__"`)
- [x] 6.3 Add a test that populate without the env var writes no rows

## 7. Fragment / duplicate exclusion (spec: Deck excludes fragment and duplicate concepts)

- [x] 7.1 Normalize concepts for comparison in `promote_concept_to_deck` and skip when a duplicate deck question exists (`re.sub(r"[^a-z0-9]+", " ", lowered)`)
- [x] 7.2 Keep existing `_is_subsumed_single_word` fragment exclusion and add tests for capitalization/normalized duplicates (`atp`/`ATP notes`) and fragments (`cellular` vs `cellular respiration`)

## 8. Verification

- [x] 8.1 Run the full test suite (`tracker_app/tests`) and `ruff check`; all existing tests must pass unmodified unless a spec update requires otherwise
- [x] 8.2 Manually verify end-to-end with a live capture (OCR + browser ingest): deck item answers show real excerpts, quiz references them, graph shows co-occurrence edges, telemetry counts grow, no `ocr`/`browser:` contexts
