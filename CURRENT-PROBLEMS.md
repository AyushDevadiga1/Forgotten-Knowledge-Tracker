# Current Problems — FKT

> Last updated: 2026-08-22
> Source: `docs/project-metrics/HEALTH.md` (full analysis)

---

## Problem 1: Two Memory Systems That Disagree

**Severity: Architectural**

The deck (LearningItem + SM-2) and the concept graph (TrackedConcept + AWFC) are two parallel memory systems that barely communicate.

- **Deck brain:** User reviews flashcards, rates AGAIN/HARD/GOOD/EASY, SM-2 schedules next review
- **Concept brain:** Micro-quiz answers feed AWFC decay, graph memory scores updated
- **Bridge is one-way:** Keywords promote from concept graph → deck. But acing a deck card never updates the concept's graph score.

**Impact:** User sees two conflicting pictures of what they know.

---

## Problem 2: Deck Auto-Pollution

**Severity: High**

`concept_promotion.py` auto-promotes keywords into the review deck with placeholder answers:

> "Captured from your study session: \<window title\>"
> "Automatically tracked... write down what you know about this concept."

There is no triage queue. Keywords flood the deck unchecked.

**Impact:** Review deck fills with unverifiable keyword cards.

---

## Problem 3: Single Quiz Question Type

**Severity: High**

`quiz_engine.py` generates exactly one shape: "Which of these concepts have you been studying?" (recognition among distractors).

No cloze deletions. No typed recall. No fill-in-the-blank. Always recognition-only.

**Impact:** User always answers the same kind of question. Learning plateaus.

---

## Problem 4: Rich Telemetry, Zero Dashboards

**Severity: High**

The tracking loop collects 6 signals (OCR text, audio label, webcam attention, cognitive load, intent, window titles) every 5s cycle. All persisted to DB. None shown to user.

Tables with zero UI surfaces: `TrackingSession`, `DailySummary`, `MultiModalLog`, `MemoryDecay`, `Metric`, `SystemSession`.

No "what did I study today", no timeline, no attention heatmap, no cognitive-load view.

**Impact:** Massive data collection with no user payoff.

---

## Problem 5: Dead-End UI Elements

**Severity: Medium**

| What looks clickable | What happens |
|---------------------|-------------|
| Knowledge Base rows (cursor-pointer) | No onClick handler, no detail view |
| Quiz results (correct/wrong) | Component state, vanishes on navigation |
| Trend chart | Bare sparkline, 1 of 6 dimensions shown |
| Cmd+K search hint | No palette component exists |
| Socket.IO `stats_update` | No frontend consumes it |

**Impact:** User expects functionality that doesn't exist.

---

## Problem 6: Features Built But Unreachable

**Severity: Medium**

| Feature | Server-side code | Missing |
|---------|-----------------|---------|
| Search items | `repository.py:169 search_items` | API endpoint + UI |
| Archive/unarchive | `learning_tracker.py` | API endpoint |
| Anki export | `learning_tracker.py export_items()` | API endpoint |
| Intent accuracy stats | `repository.py:231 get_accuracy_stats` | API endpoint |
| Daily tracking summary | `repository.py:247 get_daily_summary` | API endpoint |
| Trend analysis | `repository.py:272 get_trend_analysis` | API endpoint |
| correct_today / accuracy_today | `LearningTracker.get_learning_today()` | Display in UI |

**Impact:** 7 features work server-side but users can't reach them.

---

## Problem 7: God Module

**Severity: Medium**

`web/api.py` is 748 LOC with 27 routes mixing auth, CRUD, stats, graph, quiz, ingest, and session control.

**Impact:** Hard to maintain, test, or extend. Every change touches the same file.

---

## Problem 8: Cross-Process State via JSON File

**Severity: Low**

`session_state.py` shares state between tracker and web server via a JSON file + FileLock. Fragile, only works locally.

**Impact:** Race conditions under load, not production-ready.

---

## Problem 9: Broken Tooling and Stale Docs

**Severity: Low**

- `tools/launcher.py` calls `tracker_app/check_all_errors.py` which doesn't exist
- `FRONTEND_REDESIGN_PLAN.md` says "Phase A not started" though nearly all of it is implemented

**Impact:** misleading for new contributors.

---

## Problem 10: No Frontend Tests

**Severity: Medium**

Only `tsc --noEmit` type checking in CI. No smoke tests, no page renders, no component tests.

**Impact:** UI regressions silently ship.

---

## Summary

| # | Problem | Severity | Effort to fix |
|---|---------|----------|--------------|
| 1 | Two memory models disagree | Architectural | High |
| 2 | Deck auto-pollution | High | Medium (triage queue) |
| 3 | Single quiz type | High | Medium (new question types) |
| 4 | Telemetry with no dashboards | High | Medium (wire existing data) |
| 5 | Dead-end UI elements | Medium | Low (add handlers) |
| 6 | Unreachable features | Medium | Low (API + UI wiring) |
| 7 | God module (api.py) | Medium | Medium (refactor) |
| 8 | JSON file state sharing | Low | Medium (proper IPC) |
| 9 | Broken tooling / stale docs | Low | Low |
| 10 | No frontend tests | Medium | Medium |

---

## What's Working Well

- 378 passing tests, 0 failures
- Privacy-first design (redaction, PII filtering, sensitive window skipping)
- Modular tracking pipeline (OCR, audio, webcam, CLE are independent)
- Clean React frontend with dark theme and reduced-motion support
- Auth, rate limiting, CSRF protection all wired correctly
- Concept filtering: ML-based intent classifier + keyword blacklist + context-aware filtering
- Extraction pipeline: deduplication, UI chrome filtering, multi-word span merging, NER promotion

---

*See `docs/project-metrics/HEALTH.md` for the full deep-dive analysis.*