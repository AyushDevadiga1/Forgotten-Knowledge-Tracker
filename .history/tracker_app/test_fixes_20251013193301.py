# final_test.py
from core.audio_module import extract_features, record_audio, classify_audio
from core.intent_module import predict_intent
from core.ocr_module import ocr_pipeline
from core.webcam_module import webcam_pipeline
import numpy as np

def run_final_test():
    print("=== FINAL SYSTEM VERIFICATION ===\n")
    
    # Test 1: Audio System
    print("1. Testing Audio System...") #jjjeoijfjfijiojoijwoijoiwjroiwjeriojewiorjoirjiewrjiwejrioewjriewjrioewjrioewjriojewirjewirjewirw 
    try:
        audio_data = record_audio(duration=2)
        features = extract_features(audio_data)
        label, confidence = classify_audio(audio_data)
        print(f"   ✅ Audio: {label} (confidence: {confidence:.2f})")
        print(f"   Feature shape: {features.shape}")
    except Exception as e:
        print(f"   ❌ Audio failed: {e}")
    
    # Test 2: Intent Classification
    print("\n2. Testing Intent Classification...")
    try:
        intent_result = predict_intent(
            ocr_keywords={"python": 0.8, "code": 0.7},
            audio_label="speech", 
            attention_score=80,
            interaction_rate=12
        )
        print(f"   ✅ Intent: {intent_result['intent_label']} (confidence: {intent_result['confidence']:.2f})")
    except Exception as e:
        print(f"   ❌ Intent failed: {e}")
    
    # Test 3: OCR System
    print("\n3. Testing OCR System...")
    try:
        ocr_result = ocr_pipeline()
        keyword_count = len(ocr_result.get('keywords', {}))
        print(f"   ✅ OCR extracted {keyword_count} keywords")
        if keyword_count > 0:
            sample_keywords = list(ocr_result['keywords'].keys())[:3]
            print(f"   Sample keywords: {sample_keywords}")
    except Exception as e:
        print(f"   ❌ OCR failed: {e}")
    
    # Test 4: Webcam System
    print("\n4. Testing Webcam System...")
    try:
        webcam_result = webcam_pipeline(3)
        print(f"   ✅ Webcam: {webcam_result['face_count']} faces, attention: {webcam_result['attentiveness_score']}")
    except Exception as e:
        print(f"   ❌ Webcam failed: {e}")
    
    # Test 5: Database
    print("\n5. Testing Database...")
    try:
        from core.db_module import init_all_databases
        init_all_databases()
        print("   ✅ Database initialized successfully")
    except Exception as e:
        print(f"   ❌ Database failed: {e}")
    
    print("\n=== FINAL VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    run_final_test()