# FKT-F-005 � context_keywords non-JSON fallback ? FeedbackTrainingSample.feature_vector garbage ? retraining silently starved

- ID: FKT-F-005
- STATUS: VERIFIED
- SEVERITY: MEDIUM
- SCOPE: tracker_app.db.models.IntentPrediction/FeedbackTrainingSample JSON-in-String contract ? producers/consumers
- LOCATION:
  - tracker_app/tracking/activity_monitor.py:61 � `context_keywords=json.dumps(features) if features else (context or "")` ? raw window title when features falsy
  - tracker_app/web/api.py:74-82 � FeedbackService.record_feedback copies `feature_vector=pred.context_keywords or "[]"` verbatim into FeedbackTrainingSample (nullable=False "JSON" column, models.py:335)
  - tracker_app/scripts/train_models_from_logs.py:163-171 � `json.loads(s.feature_vector)` + len==6 gate; non-JSON ? skipped silently
  - Model contract: models.py:180 `context_keywords` documented "JSON: [f1..f6] feature vector"; migration 008 comment (migrations.py:100-104) says window title "is context, not a substitute for the features"
- CLAIM: When the classifier produces no features, activity_monitor stores the window title in a column documented as JSON. api.py copies it verbatim into the training-sample feature_vector. The trainer silently skips such samples, so user corrections on these common rows never contribute to retraining � and a `feature_vector` that is a window title is persisted in a NOT NULL column documented as JSON.
- EXPECTED: feature_vector must always be JSON (or the sample must not be created); non-JSON context_keywords must not be forwarded into the training pipeline.
- OBSERVED: Live DB: intent_predictions rows have context_keywords = 'FKT - Antigravity IDE' / 'New Tab - Google Chrome' (window titles); feedback_training_samples has one row feature_vector='FKT - Antigravity IDE'. Test acknowledges the format gap: tracker_app/tests/test_feedback_pipeline.py:133-143 (legacy window-title vector skipped gracefully).
- EVIDENCE: contract-hunter H5 (live rows), api.py:74-82 read, activity_monitor.py:55-64 read, train_models_from_logs.py:163-171.
- REPRODUCTION: CONFIRMED � end-to-end repro on throwaway DB + read-only live-DB corroboration (see REPRODUCTION/STATUS below)
- ROOT_CAUSE: (tentative) producer fallback violates documented JSON contract; bridge (api.py) does not validate before forwarding.
- RELATED_PATTERN: P-005
- AFFECTED_INSTANCES: (pending)
- FIX: Implemented (patch-engineer, 2026-08-13) as OpenSpec change `enforce-feature-vector-json-contract`:
  - `tracker_app/tracking/activity_monitor.py:61` � `IntentValidator.log_prediction` fallback is now always valid JSON: `context_keywords = json.dumps(features) if features else "[]"` (window title stays in its own `window_title` column).
  - `tracker_app/web/api.py` � `FeedbackService.record_feedback`: before creating `FeedbackTrainingSample`, `pred.context_keywords` is parsed with `json.loads` (wrapped in try/except for `json.JSONDecodeError`/`TypeError`); a sample is created only when the parsed value is a `list` of length 6. Otherwise a warning is logged and sample creation is skipped � `user_feedback`, `feedback_timestamp`, `actual_intent`, and the accuracy update still happen. The trainer's `len(feats) == 6` gate remains the final safety net; legacy malformed rows are unchanged.
- OPENSPEC_CHANGE: enforce-feature-vector-json-contract
- REGRESSION_TEST: Added `TestFeatureVectorJsonContract` in `tracker_app/tests/test_feedback_pipeline.py` (in-memory engines, existing harness; harness now also rebinds `activity_monitor.SessionLocal` per-test, the same module-scope-importer convention as test_api.py):
  - `log_prediction(features=None, context='Some Window Title')` stores `context_keywords == '[]'` (valid JSON) with the title in `window_title`;
  - `record_feedback` on a prediction with non-JSON `context_keywords` (window title) records feedback (`user_feedback`/`actual_intent`/`feedback_timestamp`) but creates NO `FeedbackTrainingSample`;
  - JSON but non-list (`'3'`) and wrong-length (`'[]'`) vectors also skip sample creation;
  - positive control: `log_prediction(features=[...6...])` -> `record_feedback` still round-trips the exact vector into `FeedbackTrainingSample.feature_vector`.
  - Verified 4 of these tests fail against the pre-fix code (fails-before-patch). Existing `test_string_false_is_treated_as_false` fixture updated from `'[]'` to a real 6-vector (assertions unchanged) because the new length-6 gate intentionally no longer persists `[]` as a training sample.
- VERIFICATION: `venv\Scripts\python.exe -m pytest tracker_app/tests/test_feedback_pipeline.py -q` -> 14 passed; full suite `venv\Scripts\python.exe -m pytest tracker_app/tests -q` -> 252 passed, 0 failed (all existing tests incl. legacy-format test green). tracker_app/data/sessions.db untouched (git status clean).
- REMAINING_RISK: fix direction (guard at producer vs bridge vs trainer) needs evidence; behavior of existing rows unchanged.

## REPRODUCTION / STATUS � bug-reproducer (evidence gate)

- CLASSIFICATION: **CONFIRMED**
- DATE: 2026-08-13
- REPRODUCER: bug-reproducer (big-pickle)
- REPO STATE: read-only. All writes to throwaway DB under C:\Users\hp\AppData\Local\Temp\opencode; live DB only read via a copy (sessions.db + -shm + -wal copied to temp, opened `?mode=ro`).

### Intended invariant (from evidence)
- models.py:180 `context_keywords = Column(String)   # JSON: [f1..f6] feature vector`
- models.py:335 `feature_vector = Column(String, nullable=False)   # JSON: [f1, f2, f3, f4, f5, f6]`
- migrations.py:100-104 (008): window title "is context, not a substitute for the features"
- activity_monitor.py:46-53 docstring: `features` is the exact 6-element vector "JSON-encoded into context_keywords so feedback-driven retraining ... gets real inputs, not a window-title string"
- train_models_from_logs.py:163-171: samples are consumed only when `json.loads(feature_vector)` succeeds AND `len(feats) == 6`; else silently `skipped += 1`.

### Repro 1 � producer fallback stores non-JSON (throwaway DB, current code)
Command (fresh subprocess, FKT_TEST_DB set before imports):
  `python f005_probe.py`  (probe in temp dir, PYTHONPATH=repo root)
Key calls:
  `IntentValidator().log_prediction('idle', 0.5, context='FKT - Antigravity IDE', features=None)`
  `FeedbackService.record_feedback(pid, is_correct=False, actual_intent='Coding')`
  `load_feedback_samples()`
Output (excerpt):
  [1] context_keywords stored: 'FKT - Antigravity IDE'
  [1] json.loads(context_keywords) RAISED: JSONDecodeError - Expecting value: line 1 column 1 (char 0)
  [2] feature_vector stored: 'FKT - Antigravity IDE'
  [2] predicted_label: 'idle' actual_label: 'Coding' window_title: 'FKT - Antigravity IDE'
  [2] json.loads(feature_vector) RAISED: JSONDecodeError - Expecting value: line 1 column 1 (char 0)
  [3] load_feedback_samples -> X_fb: []   y_fb: []
  [TrainIntent] WARNING: Skipped 1 feedback samples with malformed feature vectors.
Expected: context_keywords/feature_vector must be JSON (or no sample created); a user correction on the row must reach retraining.
Observed: window title persisted verbatim into both JSON-documented columns (api.py:76 `feature_vector=pred.context_keywords or "[]"`); the correction was silently dropped by the trainer.

### Repro 2 � positive control round-trips (same throwaway DB)
  `IntentValidator().log_prediction('studying', 0.9, context='FKT - Antigravity IDE', features=[3.0,0.0,45.0,2.0,0.4,0.7])`
  `FeedbackService.record_feedback(pid2, is_correct=False, actual_intent='studying')`
Output:
  [4] context_keywords stored: '[3.0, 0.0, 45.0, 2.0, 0.4, 0.7]'  -> json.loads OK, len = 6
  [4] feature_vector stored: '[3.0, 0.0, 45.0, 2.0, 0.4, 0.7]'     -> json.loads OK, len = 6
  [4] load_feedback_samples -> X_fb: [[3.0, 0.0, 45.0, 2.0, 0.4, 0.7]]  y_fb: ['studying']
Shows the defect is specific to the falsy-features fallback, not the pipeline as a whole.

### Repro 3 � live DB corroboration (read-only on copy; tracker_app/data/sessions.db)
Query: count rows where `json.loads(value)` fails (or is not a 6-list).
  intent_predictions total: 993
  intent_predictions context_keywords NOT valid JSON: 992
      distinct values incl. 'FKT - Antigravity IDE' (638), 'Optimizing the Neural Network | Video 9 | CampusX - YouTube - Brave', 'cnn-for-fashion-mnist.ipynb - Colab - Google Chrome', 'Claude', 'Unknown', 'New Tab - Google Chrome', ...
      1 row parses as JSON but is the scalar '3' (also not a 6-vector; skipped by len==6 gate)
  feedback_training_samples total: 1
  feedback_training_samples feature_vector NOT valid JSON: 1
      row: (id=1, timestamp='2026-08-07 14:17:34', feature_vector='FKT - Antigravity IDE', predicted_label='idle', actual_label='Coding', confidence=0.7, window_title='')
  => The only user correction ever stored has a window-title feature_vector; trainer json.loads raises and the sample is silently skipped (trainer code path verified in Repro 1).
  Latest run rows (id>=913, 2026-08-07) also store non-JSON context_keywords, e.g. id 913-915 with classifier confidences 0.9807/0.9819 but context_keywords='FKT - Antigravity IDE'.

### Naming note
The probe plan said "ActivityMonitor().log_prediction(...)"; ActivityMonitor has no log_prediction method. The actual producer is `IntentValidator.log_prediction` (activity_monitor.py:46-72), reached in production via `ActivityMonitor.process_intent` (activity_monitor.py:221-234) and `loop.py:391`. The fallback at activity_monitor.py:61 is the line exercised.

### Sibling/related observation (not part of classification)
Even JSON-parseable rows are not guaranteed 6-element vectors (live scalar '3'); the trainer len==6 gate skips those too. Fix boundary (producer guard vs bridge validation vs trainer tolerance) remains unresolved.

### Commands used
- `python f005_probe.py` (throwaway DB, FKT_TEST_DB=C:\Users\hp\AppData\Local\Temp\opencode\f005_probe.db)
- `python f005_live.py` / `f005_live4.py` (read-only query of copied live DB)
- Live DB not modified (only copied).
