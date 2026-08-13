# Context pack: FKT-F-005 — context_keywords non-JSON fallback → feature_vector garbage

## Candidate statement (exact)
"When the classifier produces no features, activity_monitor stores the window title in a column documented as JSON. api.py copies it verbatim into the training-sample feature_vector. The trainer silently skips such samples, so user corrections on these common rows never contribute to retraining — and a feature_vector that is a window title is persisted in a NOT NULL column documented as JSON."

## Contract evidence
- models.py:180 `context_keywords = Column(String)   # JSON: [f1..f6] feature vector`.
- models.py:335 `feature_vector = Column(String, nullable=False)   # JSON: [f1..f6]`.
- migrations.py:100-104 (008) comment: window title "is context, not a substitute for the features".
- activity_monitor.py:46-53 docstring: "features is the exact 6-element feature vector the classifier saw — JSON-encoded into context_keywords so feedback-driven retraining ... gets real inputs, not a window-title string."
- Producer fallback violating it: activity_monitor.py:61 `context_keywords=json.dumps(features) if features else (context or "")`.

## Source locations (minimal)
- tracker_app/tracking/activity_monitor.py:46-66 (`log_prediction`, :61 fallback).
- tracker_app/web/api.py:58-85 (`FeedbackService.record_feedback`, :76 `feature_vector=pred.context_keywords or "[]"` verbatim forward).
- tracker_app/scripts/train_models_from_logs.py:153-177 (`load_feedback_samples`, :164 `json.loads` + :165 len==6 gate, :170-171 silent skip).
- Trained-on test documenting the gap: tests/test_feedback_pipeline.py:133-143 ("legacy window-title vector is skipped gracefully").

## Reproduction (temp DB; live DB read-only)
1. `$env:FKT_TEST_DB='C:\Users\hp\AppData\Local\Temp\opencode\f005.db'` set BEFORE any import; run a fresh `venv\Scripts\python.exe -c` probe:
   - `from tracker_app.tracking.activity_monitor import IntentValidator; v=IntentValidator(); v.log_prediction('idle', 0.5, context='FKT - Antigravity IDE', features=None)`.
   - Then `from tracker_app.web.api import FeedbackService; FeedbackService.record_feedback(<pid>, is_correct=False, actual_intent='studying')`.
   - Inspect: intent_predictions.context_keywords == 'FKT - Antigravity IDE' (non-JSON); feedback_training_samples.feature_vector == 'FKT - Antigravity IDE'.
   - `from tracker_app.scripts.train_models_from_logs import load_feedback_samples; X_fb, y_fb = load_feedback_samples()` → X_fb==[] , y_fb==[] (sample silently skipped).
2. Live read-only: `SELECT context_keywords FROM intent_predictions WHERE context_keywords NOT LIKE '[%' LIMIT 5` and `SELECT feature_vector FROM feedback_training_samples` on tracker_app/data/sessions.db — finding reports window-title strings present.

## Assertion points
- `json.loads(intent_predictions.context_keywords)` raises for the fallback row.
- `json.loads(feedback_training_samples.feature_vector)` raises (or len != 6) → skipped.
- Contract direction: with `features=[...6 floats]`, everything round-trips (positive control via test_feedback_pipeline.py:119-131).

## Traps
- record_feedback imports SessionLocal inside the function — for in-process probes, rebind `models.SessionLocal` (and `activity_monitor.SessionLocal`, captured at import) to a temp-engine sessionmaker, or set FKT_TEST_DB in a fresh subprocess (preferred).
- Do not run `load_feedback_samples` against the real DB.
- Test test_feedback_pipeline.py:133-143 asserts the skip is "graceful" — the finding is the CONTRACT violation (non-JSON in JSON-documented column), not a test failure.

## Unresolved
- Fix boundary: producer guard vs bridge validation vs trainer tolerance; which is least invasive without changing stored-row behavior.
