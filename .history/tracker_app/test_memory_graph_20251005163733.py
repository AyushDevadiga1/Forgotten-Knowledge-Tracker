# ==========================================================
# ocr_module_v2_test.py
# Standalone test for core/ocr_module.py (v2)
# ==========================================================

from core.ocr_module import ocr_pipeline_v2

def test_ocr_module():
    print("🟢 Starting OCR Module v2 Test...\n")

    # Run OCR pipeline
    result = ocr_pipeline_v2()

    # Print raw OCR text snippet
    print("📄 Raw Text Snippet (first 500 chars):")
    print(result['raw_text'][:500], "\n")

    # Print old-style keywords
    print("🔑 Extracted Keywords (old pipeline):")
    for k, v in result['keywords'].items():
        print(f"{k}: score={v['score']:.2f}, count={v['count']}")

    print("\n💡 Extracted Concepts (v2):")
    for concept in result['concepts_v2']:
        print(f"- {concept}")

    print("\n📊 Embedding (v2) shape:", len(result['embedding_v2']))
    print("✅ Test completed.")

if __name__ == "__main__":
    test_ocr_module()
