## Why

Confirmed audit finding FKT-F-005: `activity_monitor.py:61` stores the raw window title in `context_keywords` when the classifier produces no features, violating the documented JSON contract (`models.py:180` "JSON: [f1..f6] feature vector"; migration 008 comment says window title "is context, not a substitute for the features"). `api.py:76` (`FeedbackService.record_feedback`) copies that value verbatim into `FeedbackTrainingSample.feature_vector` (a NOT NULL column documented as JSON), and the trainer (`train_models_from_logs.py:163-171`) silently skips such samples. Reproduced end-to-end; live DB: 992/993 `intent_predictions` rows have non-JSON `context_keywords`, and the only `feedback_training_samples` row contains a window title — user corrections never reach retraining.

## What Changes

- `tracker_app/tracking/activity_monitor.py`: the fallback stores valid JSON — `context_keywords = json.dumps(features) if features else "[]"` (window title already has its own column, `window_title`).
- `tracker_app/web/api.py` `FeedbackService.record_feedback`: validate before persisting a training sample — only create `FeedbackTrainingSample` when `pred.context_keywords` parses as JSON and is a list of length 6; otherwise skip sample creation with a logged warning (the user feedback + accuracy update still happen).
- Legacy/other non-JSON rows are unaffected; the trainer already skips them.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
`feedback.training-sample`: produced `feature_vector` values are always valid JSON (6-vector or "[]"); malformed legacy values are never forwarded into new training samples.

## Impact

- Modified: `tracker_app/tracking/activity_monitor.py`, `tracker_app/web/api.py`
- Behavior change: corrections attached to predictions without a real feature vector no longer create a garbage training sample (they still record the correction itself).
- Existing malformed rows in the live DB are not rewritten (out of scope; they were already being skipped).

## Notes

- The trainer's `len(feats) == 6` gate remains the final safety net.
