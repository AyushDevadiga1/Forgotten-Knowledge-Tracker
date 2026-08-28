## Context

See `proposal.md` — Why. Current pipeline: OCR and browser ingest extract keyword concepts but persist no body text (`ConceptEncounter.context_snippet` gets literal `"ocr"` or `"browser:<title>"`); deck answers are template placeholders built in `concept_promotion._answer_for`; the micro-quiz asks a keyword self-report; the graph has only 13 semantic edges (138 nodes); `multi_modal_logs`/`metrics` have no runtime writers; `tools/populate.py` seeds the real DB; promotion accepts fragments/duplicates.

Constraints from the codebase: `ConceptEncounter.context_snippet` already exists (`db/models.py:284`) — no schema/migration work needed. Privacy pipeline already exists (`privacy_filter`: `sanitize_text_for_storage`, `is_sensitive_window`, `strip_redaction_markers`, `filter_sensitive_keywords`) and must stay the gate before anything is persisted. `CONTEXT_MAX_LENGTH` (200) is already enforced in `concept_scheduler.add_concept`.

## Goals / Non-Goals

**Goals:**
- Real captured text is persisted (sanitized, capped) as encounter context from both capture paths.
- Deck answers derive from that text; auto-promotion is blocked when no real content exists.
- Micro-quiz only offers content-backed concepts and never the keyword self-report template.
- Graph gains co-occurrence edges from real capture windows.
- Tracking loop writes `multi_modal_logs` + `metrics`; telemetry reflects runtime captures.
- `populate.py` cannot touch the default DB without explicit enablement, and marks its runs.
- Promotion/backfill excludes fragment and duplicate concepts.

**Non-Goals:**
- No LLM/summarization of captured text (answers are excerpts, not generated explanations).
- No schema migrations (column exists).
- No rewrite of the SM-2/AWFC math; P6 is a verification/test task only.
- Historical placeholder items already in the deck are not rewritten.

## Decisions

### D1 — Persist sanitized excerpts into the existing `context_snippet`
Reuse the privacy/quality filters already on each path, then store the excerpt. No new columns.
- OCR: `ocr_pipeline` already returns `raw_text`; sanitize it before returning (`sanitize_text_for_storage` → drop if not `safe_to_store` → `strip_redaction_markers`), cap 500 as today. `loop.py` passes `context=raw_text[:CONTEXT_MAX_LENGTH]` into `process_concepts`, which forwards it to `add_concept` (replacing the hard-coded `"ocr"`).
- Browser: `ingest.py` passes `validation["cleaned_text"][:CONTEXT_MAX_LENGTH]` (already safe) as `context` instead of `f"browser:{title}"`.
- `activity_monitor.process_concepts(ocr_keywords, ..., context_text="")`.
- No title fallback: empty text ⇒ empty context ⇒ promotion gate blocks (D2).
- Rationale: single persisted field already threaded end-to-end; alternatives (new columns, graph-node payloads) add schema/migration cost for no behavioral gain.
- Alternative considered: persist original 500-char text in a new column — rejected, no need.

### D2 — Content-gated promotion and content-derived answers
`_answer_for` returns `None` when the newest context snippet is empty / `"ocr"` / shorter than 8 chars. `promote_concept_to_deck` (and therefore `backfill_items`) skips the concept (returns `None`, logs) when the answer is `None`. Otherwise the answer is the (prefix-stripped) excerpt directly.
- Old `browser:`-prefixed rows strip their prefix; the placeholder template string is removed from the codebase.
- Rationale: this is exactly the "garbage out" seam — block promotion until real content exists.
- Trade-off: fewer deck items until the user captures real text; accepted (spec: no placeholder answers).

### D3 — Content-backed micro-quiz pool
`generate_micro_quiz` builds its candidate pool from concepts whose latest encounter has a real excerpt (query `ConceptEncounter`, group by concept, `len(snippet)>8`, not `"ocr"`). The MC stem becomes `"Which of these concepts does this captured material cover?"` with the excerpt shown. If the pool is empty, return `None` (no quiz emitted). Distractors stay: semantic neighbours then random concepts.
- Rationale: honest, content-referencing questions with today's data; no external generation dependency.

### D4 — Co-occurrence edges from capture windows
New `knowledge_graph.record_capture_window(concepts)`: for each unordered pair in one capture window, increment a counter and set edge weight `min(1.0, count / window_to_weight)` with `reason="cooccur"`; cap each window to 30 pairs (top by frequency) to bound density. Called from `loop.py` and `ingest.py` with the window's keyword set. Existing embedding edges stay.
- Rationale: encodes the only real relational signal the system has (what the user actually co-studied).
- Risk: dense graph growth → bound via the existing `MAX_GRAPH_NODES`/eviction and window pair cap.

### D5 — Runtime telemetry writers
Add `TrackingRepository.log_multimodal(...)` inserting a `MultiModalLog` row from each active capture cycle (window title, JSON keywords, audio label, attention, interaction rate, intent, confidence, memory_score). At session end, write one `Metric` row per distinct session concept (AWFC memory score). `export_tracking_data` (JSON) stays.
- The telemetry summary's 24h query then reads real rows; seed rows age out.
- Risk: row volume — a row per cycle is required by the spec; acceptable for the desktop scale this targets.

### D6 — Seed guard + marker
`populate.py main()` aborts with a message and writes nothing unless `FKT_SEED=1` is set in the environment. When enabled, it writes its rows and adds a single `Metric` row (`concept="__seed__"`) so a seeded DB is identifiable. No new table/migration (avoids touching schema for a dev tool).
- Rationale: keeps demo data out of the default DB by default; marker lets audits distinguish seed from real.

### D7 — Fragment/duplicate filter at promotion
In `promote_concept_to_deck`, before accepting, normalize the concept (`re.sub(r"[^a-z0-9]+", " ", lowered)`) and skip if it equals an existing `learning_items` question's normalized form (duplicate), or if `_is_subsumed_single_word` reports a fragment (existing). Covers `atp`/`ATP notes` dupes and `cellular` vs `cellular respiration`.
- Rationale: closes the remaining noise path without touching captured data.

## Risks / Trade-offs

- [Fewer deck items until content exists] → intended per spec; triage still lets users add manually.
- [Telemetry row volume] → bounded by one row per capture cycle; revisit with batching if the DB grows large.
- [Co-occurrence edge spam on broad windows] → capped pairs per window + existing eviction.
- [Excerpts may read like noise] → they are raw excerpts; user-facing answer text is trimmed to `CONTEXT_MAX_LENGTH` and prefix-stripped.

## Migration Plan

No schema changes. Deployment = code deploy. Historical placeholder deck items and old `"browser:"`/`"ocr"` contexts are left intact (untouched by this change). Rollback = revert the code change; nothing destructive occurs.

## Open Questions

None — all unknowns above are resolved in the decisions; deferred choices (exact pair-cap / weight thresholds) are tunable constants that do not change the specs.
