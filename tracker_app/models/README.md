# FKT Machine Learning Models

This directory contains trained machine learning models for the Forgotten Knowledge Tracker.

## Model Files

- **intent_classifier.pkl** (~3 MB) — Intent classification model (RandomForest,
  6-feature vector, ADR-003). Trained via:

  ```bash
  python -m tracker_app.scripts.train_models_from_logs
  ```

  If it is absent, `intent_module.py` falls back to rule-based classification —
  a missing model is expected, not a bug.

## Audio Classification

There is **no** audio model, by design. FKT previously shipped a "trained"
`audio_classifier.pkl` generated from synthetic random MFCC vectors — a stub
that created a false sense of model quality (see ADR-002 and the makeover
audit's C-4). The synthetic trainer and its model-loading path were removed;
`audio_module.py` classifies audio with deterministic energy/RMS/ZCR heuristics.
If a real audio training pipeline is ever built, the loader can be re-added.

## Adding New Models

1. Place your trained `.pkl` or `.h5` files here
2. Update `tracker_app/config.py` with model path constant
3. Update relevant module (`intent_module.py`, `audio_module.py`, etc.)

## Model Size

Keep individual model files <50MB. For larger models:
- Use model compression
- Store externally (S3, GCS) and download on first run
- Add to `.gitignore` and provide download script
