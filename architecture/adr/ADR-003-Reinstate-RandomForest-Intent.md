# ADR-003: Reinstatement of RandomForest Intent Classifier (Phase 9 Reversal of ADR-002)

## Status
Accepted — supersedes the decision in ADR-002 for Intent Classification only.

## Context
ADR-002 removed all ML classifiers in favour of pure heuristics after discovering the original models were trained on synthetic/arbitrary data (effectively encoding `if-else` logic into tree structures).

During Phase 9, this proved insufficient: strict heuristics failed on edge cases for **Intent Classification** specifically (e.g., distinguishing between `studying` and `browsing` when keyboard and audio signals both indicated high engagement).

## Decision
We reintroduced `scikit-learn` specifically for the Intent Prediction pipeline using a lightweight `RandomForestClassifier` (`tracker_app/tracking/intent_module.py`).

Audio classification retains the deterministic heuristic approach from ADR-002 (no revert needed there — it is genuinely simple enough for rules).

## Architecture
The Intent system now uses a **Hybrid Approach**:
1. A `RandomForestClassifier` is used for intent predictions at runtime.
2. If the user corrects a prediction via the web dashboard (`IntentFeedbackToast`), the corrected label is written to `feedback_training_samples` via `FeedbackRepository`.
3. Every 50 corrections, `scripts/train_models_from_logs.py` is invoked by a background thread; it retrains the model and swaps it in if accuracy improves.
4. The feedback loop data is also available for manual retraining via `python -m tracker_app.scripts.train_models_from_logs`.

## Rationale
- The classifier learns from **actual user behaviour**, not synthetic data — the core issue in ADR-002 is avoided.
- `scikit-learn` is already a dependency for `hdbscan` (concept clustering), so no new top-level dependency is added.
- The fallback to heuristics (if no trained model exists) is retained.

## Consequences
- **Positive**: Intent prediction improves over time for each specific user.
- **Positive**: `requirements.txt` does not grow — `scikit-learn` was already required.
- **Negative**: Cold-start accuracy is no better than heuristics until ~50 feedback samples are collected.
