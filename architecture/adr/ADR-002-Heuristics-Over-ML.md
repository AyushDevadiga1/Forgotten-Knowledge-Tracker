# ADR-002: Heuristics over Synthetic ML Classification

## Status
Accepted

## Context
FKT previously shipped with two Machine Learning classifiers (`intent_classifier.pkl`, `audio_classifier.pkl`) built via scikit-learn and XGBoost. During Phase 4 Evaluation, it was discovered that these binaries were trained on entirely arbitrary synthetic randomization logic with explicit hardcoded relationships (e.g. `high_keys = 'studying'`).

## Decision
We removed the Machine Learning `.pkl` bundles, purged the heavy mathematical dependencies (`scikit-learn`, `xgboost`), and implemented bare-bones deterministic logic statements natively in the Python modules (`audio_module.py`, `intent_module.py`).

## Rationale
1. *Occam's Razor*: A deterministic `if-else` statement is orders of magnitude less complex, easier to debug, and functionally identical to an XGBoost tree explicitly trained to mirror that exact `if-else` statement. 
2. Heavy package sizes bloat user downloads and memory footprint.
3. "Cargo cult AI" provides no real empirical user tracking benefits.

## Consequences
- **Positive**: Application boots faster, installation is smaller, and predictions are predictably configurable by simply changing a threshold integer block.
- **Negative**: N/A. (The previous "ML" wasn't learning or improving anyway).

## Update (Phase 9 Reversal)
During Phase 9, we realized strict heuristics failed on edge cases for Intent Classification. We **reintroduced `scikit-learn`** specifically for the Intent Prediction model using a lightweight `RandomForestClassifier`. 
The system now uses a **Hybrid Approach**:
1. It uses the `RandomForestClassifier` for intent predictions.
2. If the user corrects the prediction via the web dashboard, the feedback is saved.
3. Every 50 corrections, a background thread silently auto-retrains the model and swaps it in if accuracy improves.
This gives us the best of both worlds: a real ML model that actually learns from the user over time, without the bloat of deep learning libraries.
