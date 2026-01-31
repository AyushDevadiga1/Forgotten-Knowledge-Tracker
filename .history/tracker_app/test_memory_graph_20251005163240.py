# ==========================================================
# test_ocr_v2.py
# ==========================================================

from core.ocr_module import ocr_pipeline_v2
from pprint import pprint

print("🟢 Starting OCR Module v2 Test...\n")

# Run the OCR pipeline v2
result = ocr_pipeline_v2()

# Display results
print("📄 Raw Text Snippet (first 500 chars):")
print(result['raw_text'][:500])

print("\n🔑 Extracted Keywords (old pipeline):")
for kw, info in result['keywords'].items():
    score = info['score']
    count = info['count']
    print(f"{kw}: score={score:.2f}, count={count}")

print("\n💡 Extracted Concepts (v2):")
for concept in result['concepts_v2']:
    print(f"- {concept}")

print("\n📊 Topic Scores (v2):")
for topic, score in result['topic_scores'].items():
    print(f"{topic}: {score:.2f}")

print("\n📊 Embedding (v2) shape:", len(result['embedding_v2']))
print("✅ Test completed.")
