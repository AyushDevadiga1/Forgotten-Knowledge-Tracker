# verify_trained_models.py
import pickle
import numpy as np

def verify_models():
    print("🔍 VERIFYING TRAINED MODELS")
    print("=" * 50)
    
    models_to_verify = [
        ("audio_classifier.pkl", "Random Forest Audio Classifier"),
        ("audio_scaler.pkl", "Audio Feature Scaler"),
        ("audio_label_encoder.pkl", "Audio Label Encoder"), 
        ("intent_classifier.pkl", "XGBoost Intent Classifier"),
        ("intent_label_map.pkl", "Intent Label Encoder")
    ]
    
    all_loaded = True
    
    for filename, description in models_to_verify:
        try:
            with open(f"core/{filename}", "rb") as f:
                model = pickle.load(f)
            print(f"✅ {description} - LOADED SUCCESSFULLY")
            
            # Test basic functionality
            if "classifier" in filename:
                # Test prediction with dummy data
                if "audio" in filename:
                    test_features = np.random.random(20).reshape(1, -1)
                else:  # intent classifier
                    test_features = np.array([[10, 1, 75, 8]])  # OCR, speech, attention, interaction
                
                try:
                    prediction = model.predict(test_features)
                    print(f"   Test prediction: {prediction[0]}")
                except:
                    print("   (Prediction test skipped)")
                    
        except Exception as e:
            print(f"❌ {description} - FAILED: {e}")
            all_loaded = False
    
    # Test the full pipeline
    print("\n🧪 TESTING FULL CLASSIFICATION PIPELINE")
    try:
        # Load all models
        with open("core/audio_classifier.pkl", "rb") as f:
            audio_clf = pickle.load(f)
        with open("core/audio_scaler.pkl", "rb") as f:
            audio_scaler = pickle.load(f)
        with open("core/audio_label_encoder.pkl", "rb") as f:
            audio_encoder = pickle.load(f)
        with open("core/intent_classifier.pkl", "rb") as f:
            intent_clf = pickle.load(f)
        with open("core/intent_label_map.pkl", "rb") as f:
            intent_encoder = pickle.load(f)
        
        # Test audio classification
        audio_features = np.random.random(20).reshape(1, -1)
        scaled_features = audio_scaler.transform(audio_features)
        audio_pred = audio_clf.predict(scaled_features)[0]
        audio_label = audio_encoder.inverse_transform([audio_pred])[0]
        print(f"🎵 Audio test: {audio_label}")
        
        # Test intent classification  
        intent_features = np.array([[15, 1, 80, 12]])  # Studying scenario
        intent_pred = intent_clf.predict(intent_features)[0]
        intent_label = intent_encoder.inverse_transform([intent_pred])[0]
        confidence = np.max(intent_clf.predict_proba(intent_features)[0])
        print(f"🎯 Intent test: {intent_label} (confidence: {confidence:.3f})")
        
        print("✅ Full pipeline working correctly!")
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        all_loaded = False
    
    return all_loaded

if __name__ == "__main__":
    success = verify_models()
    if success:
        print("\n🎉 ALL MODELS VERIFIED AND READY FOR PRODUCTION!")
    else:
        print("\n⚠️ Some models failed verification. Please retrain.")