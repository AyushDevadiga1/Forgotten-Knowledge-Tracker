# test_ocr_module.py
import cv2
from core.ocr_module import (
    capture_screenshot,
    preprocess_image,
    extract_text,
    extract_keywords,
    extract_concepts_v2,
    get_text_embedding_v2,
    ocr_pipeline
)

def test_with_screenshot():
    """Test OCR on live screen"""
    img = capture_screenshot()
    if img is None:
        print("❌ Failed to capture screenshot.")
        return
    
    processed = preprocess_image(img)
    text = extract_text(processed)
    print("\n--- Raw OCR Text ---")
    print(text[:500] + ("..." if len(text) > 500 else ""))

    keywords = extract_keywords(text)
    print("\n--- Extracted Keywords ---")
    for kw, info in keywords.items():
        print(f"{kw}: score={info['score']}, count={info['count']}")

    concepts = extract_concepts_v2(text)
    print("\n--- Extracted Concepts ---")
    print(concepts)

    embedding = get_text_embedding_v2(text)
    print("\n--- Embedding Vector Shape ---")
    print(embedding.shape)

def test_with_image_file(file_path):
    """Test OCR on a local image"""
    img = cv2.imread(file_path)
    if img is None:
        print(f"❌ Could not read image: {file_path}")
        return
    
    processed = preprocess_image(img)
    text = extract_text(processed)
    print("\n--- Raw OCR Text ---")
    print(text[:500] + ("..." if len(text) > 500 else ""))

    keywords = extract_keywords(text)
print("\n--- Extracted Keywords ---")
for kw, score in keywords.items():
    print(f"{kw}: score={score:.3f}")


    concepts = extract_concepts_v2(text)
    print("\n--- Extracted Concepts ---")
    print(concepts)

if __name__ == "__main__":
    print("🔹 Testing OCR on live screen...")
    test_with_screenshot()

    # Example for testing a local image file:
    # test_with_image_file("sample_screenshot.png")
