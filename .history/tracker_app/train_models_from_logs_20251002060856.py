# test_ocr_rich_keywords.py
from core.ocr_module import ocr_pipeline

if __name__ == "__main__":
    result = ocr_pipeline()
    
    print("\n===== OCR Pipeline Test =====")
    print(f"Raw text snippet (first 500 chars):\n{result['raw_text'][:500]}\n")
    
    print("Extracted keywords with scores:")
    for kw, score in result['keywords'].items():
        print(f"{kw} -> {score:.2f}")
