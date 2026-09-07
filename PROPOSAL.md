# Proposal: Offline Semantic Extraction Pipeline

## Background and Problem
The current extraction pipeline in FKT relies on **Tesseract OCR** and **YAKE + spaCy** for keyword extraction. While extremely fast and lightweight, our Golden Dataset analysis reveals critical failures in this approach:
1. **Aggressive Preprocessing Destroys Text:** The OpenCV morphological operations (Otsu + close) blur and destroy standard screen fonts, leading to near-zero OCR signal on modern web pages (e.g. `": > + q x\nbed"`).
2. **Loss of Structural Hierarchy:** Tesseract flattens all text, losing the concept of titles, headings, and sections.
3. **Lack of Semantic Understanding:** YAKE is purely statistical. It extracts keywords but has no capacity to classify a `theme` (e.g., "Deep Learning" vs "Job Search") or contextual `mode`.

We cannot reach the expected results of the `GOLDEN_DATASET.md` with statistical string counting. 

## Proposed Solution: SLM/VLM Pipeline
To achieve fully offline, privacy-first extraction of structured hierarchies and semantic themes, we propose replacing the YAKE/Tesseract pipeline with a tiered Small Language Model (SLM) architecture.

### 1. Tiered Triggers (Battery Optimization)
Heavy models shouldn't run every 20 seconds. We should use a tiered approach:
*   **Tier 1 (Instant):** Fast heuristics (window title, app name). If unchanged, do nothing.
*   **Tier 2 (Event-Driven):** Run the heavy extraction pipeline only on significant context switches (e.g., changing apps, large scroll events, or every 2-3 minutes).

### 2. Vision and Layout Extraction
Instead of Tesseract + OpenCV, use a modern, lightweight edge OCR engine (e.g., **PaddleOCR** or **Surya OCR**) that is designed for digital documents, not scanned receipts. This preserves bounding boxes and structural layout without destroying the image via thresholding.

### 3. Concept and Hierarchy Parsing (The "Brain")
Pass the extracted text + layout bounding boxes into a **quantized Small Language Model (SLM)** running locally (via `llama.cpp` or `Ollama`).
*   **Models:** `Phi-3-mini` (3.8B) or `Llama-3-8B` (4-bit quantized).
*   **Function:** The SLM will output JSON exactly matching our Golden Dataset schema, assigning semantic themes, extracting hierarchical sections, and pulling out core concepts. 

### 4. Intent Classification
Keep the **Random Forest / XGBoost** model! Once the SLM extracts the high-quality semantic features (e.g., `theme="job search"`), the lightweight Random Forest can accurately and instantly classify the `true_intent` (`studying`, `passive`, `idle`).

## Benefits
*   **Privacy-First:** Remains 100% offline. No cloud APIs required.
*   **Accuracy:** Matches the ground-truth accuracy of the Golden Dataset.
*   **Resilient:** Solves the OpenCV preprocessing bug and understands the context of the user's screen.

## Risks
*   **Resource Usage:** Running an SLM locally uses significant RAM (2-4GB) and battery. The Tiered Trigger system is absolutely mandatory to make this viable for a background application.
