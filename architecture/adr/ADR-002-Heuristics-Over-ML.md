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
