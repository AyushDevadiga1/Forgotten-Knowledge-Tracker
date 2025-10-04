if __name__ == "__main__":
    from intent_module import predict_intent

    test_samples = [
        {"ocr_keywords": ["photosynthesis"], "audio_label": "speech", "attention_score": 80, "interaction_rate": 10},
        {"ocr_keywords": [], "audio_label": "silence", "attention_score": 50, "interaction_rate": 0},
        {"ocr_keywords": ["python", "code"], "audio_label": "music", "attention_score": 50, "interaction_rate": 3},
    ]

    for sample in test_samples:
        result = predict_intent(
            sample["ocr_keywords"],
            sample["audio_label"],
            sample["attention_score"],
            sample["interaction_rate"]
        )
        print(f"Input: {sample}")
        print(f"Predicted intent: {result['intent_label']}, Confidence: {result['confidence']:.2f}\n")
