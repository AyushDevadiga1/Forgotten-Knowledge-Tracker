import pickle
import numpy as np

# Load model and label map
try:
    with open("core/intent_classifier.pkl", "rb") as f:
        intent_clf = pickle.load(f)
    with open("core/intent_label_map.pkl", "rb") as f:
        intent_label_map = pickle.load(f)
    print("Intent classifier and label map loaded.")
except Exception as e:
    print("Failed to load classifier or label map:", e)
    exit()

# Create dummy features matching your extract_features output
# Features: [ocr_count, audio_val, attention_score, interaction_rate]
dummy_features_list = [
    [0, 0, 50, 0],     # idle / low activity
    [5, 2, 80, 10],    # likely studying
    [3, 1, 30, 5],     # passive
]

for i, feats in enumerate(dummy_features_list):
    feats_array = np.array(feats).reshape(1, -1)
    try:
        pred_idx = int(intent_clf.predict(feats_array)[0])
        proba = intent_clf.predict_proba(feats_array)[0]
        confidence = float(max(proba))
        label = intent_label_map.get(pred_idx, "unknown")
        print(f"Test {i+1}: Features={feats} => Predicted: {label}, Confidence: {confidence:.2f}")
    except Exception as e:
        print(f"Test {i+1} failed! Full error:")
        import traceback
        traceback.print_exc()
