# FKT System Health — Why It Feels Monotonous

> Deep-dive analysis written 2026-08-22. Based on reading actual source code,
> not documentation or assumptions.

---

## TL;DR

The system has **rich capture** (OCR, audio, webcam attention, cognitive load,
intent classification) and **solid infrastructure** (SM-2, knowledge graph,
privacy filtering, rate limiting, auth). But the **payoff loop is broken**:
data flows in, gets processed, and never reaches the user in a meaningful way.
The result is a system that works technically but feels hollow.

---

## 1. The Two Memory Models That Disagree

**This is the core architectural problem.**

There are two parallel spaced-repetition systems that barely communicate:

### Deck brain (LearningItem + ReviewHistory)
- User manually reviews flashcards via `ReviewPage.tsx`
- Quality buttons: AGAIN(0) / HARD(2) / GOOD(4) / EASY(5)
- SM-2 scheduling feeds dashboard KPIs, trend chart, streak
- `LearningTracker.get_learning_today()` computes `correct_today` / `accuracy_today`

### Concept brain (TrackedConcept + ConceptScheduler)
- Scheduled by `concept_scheduler.py ConceptScheduler.schedule_next_review`
- Fed only by micro-quiz answers (`quiz_engine.record_quiz_result`)
- Drives graph memory scores via AWFC (`memory_model.py:74 compute_memory_score_awfc`)
- λ_p = λ_base * (1 - att_norm * 0.30), clamped [0.01, 0.50]

### The bridge is one-directional
`concept_scheduler.add_concept` → `promote_concept_to_deck()` when strength
crosses threshold. Keywords silently flood the review deck. **No reverse path**:
acing a deck card never updates the concept's graph score or schedule.

**User experience:** Deck fills with auto-promoted keywords. Graph disagrees
with quiz page. Two separate "memories" of what you know.

---

## 2. The Deck Is Auto-Polluted, Never Curated

`concept_promotion.py _answer_for()` generates placeholder answers:

> "Captured from your study session: <window title>"
> "Automatically tracked... write down what you know about this concept."

A `UI_CHROME` frozenset filters junk words. `CURATED_EXCEPTIONS_DEFAULT` has
2 entries. `curated_exceptions.txt` is user-editable. But the core loop
produces **keyword flashcards without real content**, reviewed against
nothing checkable.

There is no triage queue ("confirm these captured concepts") before items
hit the review list.

---

## 3. One Question Type, Forever

`quiz_engine.py` generates exactly one question shape:

> "Which of these concepts have you been studying?" (recognition of a name
> among distractors)

No cloze deletions. No recall-from-answer. No typed answer checking against
actual content. The quiz is always recognition-only.

---

## 4. Rich Telemetry, No Dashboards

The tracking loop collects (every 5s cadence):

| Signal | Module | Frequency | Persisted | Shown to user? |
|--------|--------|-----------|-----------|----------------|
| OCR text | `ocr_module.py` | ~20s | Yes (MultiModalLog) | **No** |
| Audio label | `audio_module.py` | ~15s | Yes (MultiModalLog) | **No** |
| Webcam attention | `webcam_module.py` | ~45s | Yes (TrackingSession) | **No** |
| Cognitive load | `cle_module.py` | every cycle | Yes (TrackingSession) | **No** |
| Intent | `intent_module.py` | every cycle | Yes (intent_predictions) | **No** |
| Window titles | loop.py | every cycle | Yes (TrackingSession) | **No** |

`TrackingSession`, `DailySummary`, `MultiModalLog`, `MemoryDecay`, `Metric`,
`SystemSession` tables have **zero UI surfaces**.

No "what did I study today", no timeline, no attention heatmap, no
cognitive-load view.

---

## 5. Dead Ends in the UI

| What looks clickable | What actually happens |
|---------------------|----------------------|
| Knowledge Base rows (cursor-pointer) | No onClick handler, no detail view |
| Quiz results (correct/wrong count) | Component state, vanishes on navigation |
| Trend chart | Bare sparkline, 1 of 6 data dimensions shown |
| ⌘K search hint in header | No palette component exists |
| Socket.IO `stats_update` event | No frontend code consumes it |

---

## 6. Features Built But Unreachable

| Feature | Server-side location | Status |
|---------|---------------------|--------|
| Search items | `repository.py:169 search_items` | Orphaned (UI filters client-side) |
| Archive/unarchive | `learning_tracker.py` | Orphaned (no API endpoint) |
| Anki export | `learning_tracker.py export_items()` | Orphaned (no API endpoint) |
| Intent accuracy stats | `repository.py:231 get_accuracy_stats` | Orphaned (no API endpoint) |
| Daily tracking summary | `repository.py:247 get_daily_summary` | Orphaned (no API endpoint) |
| Trend analysis | `repository.py:272 get_trend_analysis` | Orphaned (no API endpoint) |
| `correct_today` / `accuracy_today` | `LearningTracker.get_learning_today()` | Computed but never displayed |

---

## 7. Architecture Observations

### Strengths
- Privacy-first design (redaction, sensitive window skipping, PII filtering)
- Modular tracking pipeline (OCR, audio, webcam, CLE are independent)
- Clean React frontend with consistent dark theme and reduced-motion support
- 378 passing tests, 0 failures
- Auth, rate limiting, CSRF protection all wired correctly

### Weaknesses
- **God module:** `web/api.py` (748 LOC, 27 routes) mixing auth, CRUD, stats,
  graph, quiz, ingest, session control
- **Cross-process state via JSON file + FileLock** (`session_state.py`) —
  fragile, works only locally
- **Singleton accessors everywhere** (`get_tracker()`, `get_cle()`,
  `get_scheduler()`)
- **No frontend tests** — only `tsc --noEmit` type checking in CI
- **Broken tooling:** `tools/launcher.py launch_check` calls
  `tracker_app/check_all_errors.py` which doesn't exist
- **Stale docs:** `FRONTEND_REDESIGN_PLAN.md` says "Phase A not started"
  though nearly all of it is implemented

---

## 8. What Would Make This Feel Alive

### Quick wins (already implemented server-side, just need API + UI)
1. **Show accuracy today** — `get_learning_today()` already computes it
2. **Daily study timeline** — `get_daily_summary()` exists
3. **Knowledge base detail view** — rows already have cursor-pointer
4. **Export to Anki** — `export_items()` exists

### Medium effort (core product gaps)
5. **Triage queue** — show captured concepts before they hit the deck
6. **Richer quiz types** — cloze, typed recall, image-based
7. **Attention heatmap** — webcam attention data is persisted, just needs a chart
8. **Concept ↔ Deck sync** — bidirectional: acing a card updates graph score

### Structural improvements
9. **Break up api.py** — split into auth, items, quiz, graph, session blueprints
10. **Frontend test suite** — at least smoke tests for each page
11. **Fix broken tooling** — launcher.py, redesign docs

---

## 9. Metrics Summary

| Metric | Value |
|--------|-------|
| Total Python LOC | 14,768 (14.8 KLOC) |
| Test LOC | 4,910 |
| Test-to-code ratio | 0.33 |
| API endpoints | 27 |
| Frontend LOC | 3,410 |
| Python dependencies | 26 |
| Complexity hotspots (>200 LOC) | 18 |
| Largest file | text_quality_validator.py (868 LOC) |
| Passing tests | 378 |
| Git commits | 303 |

---

*This document should be updated as the system evolves. Next review after
the next major feature push.*