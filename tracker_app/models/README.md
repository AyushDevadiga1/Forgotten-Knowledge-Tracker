# FKT Machine Learning Models

This directory contains trained machine learning models for the Forgotten Knowledge Tracker.

## Model Files

- **intent_classifier.pkl** (740KB) - Intent classification model
- **intent_label_map.pkl** (271B) - Label mapping for intent classifier
- **audio_classifier.pkl** (343KB) - Audio context classification
- **audio_label_encoder.pkl** (348B) - Audio label encoder
- **audio_scaler.pkl** (930B) - Audio feature scaler

## Retraining Models

If you need to retrain the models with new data:

```bash
python scripts/train_models.py
```

## Model Details

### Intent Classifier
- **Algorithm**: Logistic Regression
- **Features**: TF-IDF vectorization
- **Classes**: learning, working, browsing, idle
- **Training Data**: `tracker_app/data/intent_training_data.csv`

### Audio Classifier  
- **Algorithm**: Random Forest
- **Features**: MFCC, spectral features (librosa)
- **Classes**: speech, music, noise, silence
- **Training Data**: Audio feature logs

## Adding New Models

1. Place your trained `.pkl` or `.h5` files here
2. Update `tracker_app/config.py` with model path constant
3. Update relevant module (`intent_module.py`, `audio_module.py`, etc.)

## Model Size

Keep individual model files <50MB. For larger models:
- Use model compression
- Store externally (S3, GCS) and download on first run
- Add to `.gitignore` and provide download script
