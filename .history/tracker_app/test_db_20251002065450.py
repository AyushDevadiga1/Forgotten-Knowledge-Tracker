from core.intent_module import extract_features, predict_intent

# test OCR + audio + interaction
ocr_test = {"import": {"score":1.0,"count":5}}
audio_test = "speech"
attention_test = 0
interaction_test = 0

features = extract_features(ocr_test, audio_test, attention_test, interaction_test)
print("Features shape:", features.shape)

result = predict_intent(ocr_test, audio_test, attention_test, interaction_test)
print(result)
