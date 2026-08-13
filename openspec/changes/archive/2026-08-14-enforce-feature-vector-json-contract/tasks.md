## 1. Producer: always JSON

- [x] 1.1 `tracker_app/tracking/activity_monitor.py` `IntentValidator.log_prediction`: `context_keywords = json.dumps(features) if features else "[]"` (window title already stored in its own `window_title` column)

## 2. Bridge: validate before persisting samples

- [x] 2.1 `tracker_app/web/api.py` `FeedbackService.record_feedback`: before creating `FeedbackTrainingSample`, parse `pred.context_keywords` as JSON and require a list of length 6; on failure log a warning and skip sample creation (user_feedback + accuracy update still proceed)

## 3. Regression coverage

- [x] 3.1 Test: `log_prediction(features=None, context='title')` stores `context_keywords == '[]'` (valid JSON)
- [x] 3.2 Test: `record_feedback` on a prediction with non-JSON `context_keywords` records the feedback but creates no `FeedbackTrainingSample`
- [x] 3.3 Test: positive control — a real 6-vector still round-trips into a training sample
- [x] 3.4 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green (existing legacy-format test must still pass)
