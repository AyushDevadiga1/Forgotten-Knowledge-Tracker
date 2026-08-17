# Evaluation of FKT Screenshots & Codebase Analysis

## 1. Observations from Screenshots

After reviewing the 6 screenshots in the `outputs` directory, the following issues were identified:
- **Screenshot 1 (`/` Dashboard):** The "Review trend" chart is empty, though 66 items are active. 
- **Screenshot 2 (`/review`):** Displays a legitimate concept ("mnemonics") in the spaced repetition session.
- **Screenshot 3 (`/database`):** The knowledge base lists valid concepts (atp, oxygen, glucose, etc.), but all have a 0% success rate and 0 reviews, indicating that tracked items are populated but not being actively reviewed yet.
- **Screenshot 4 (`/graph`):** The Knowledge Graph contains valid nodes like "atp energy" and "active recall", but is heavily polluted with gibberish nodes such as `aastha`, `aplaseascrt`, `aearee`, `adaya`, and `pebeoge`.
- **Screenshot 5 (`/quiz`):** The Micro-Quiz uses these gibberish strings as multiple-choice distractors (e.g., Options A, C, and D are `aastha`, `ratha`, `pebeoge`).
- **Screenshot 6 (`/add`):** Manual ingestion UI looks fine, but the system is automatically ingesting poor-quality concepts elsewhere.

**Core Issue:** The knowledge graph and quiz engine are heavily polluted with OCR garbage or text extraction noise (gibberish strings).

---

## 2. Root Cause Analysis (Codebase)

The presence of gibberish words traces back to how the system extracts and validates text from the user's screen or study session. 

### Why is this occurring?
I reviewed `tracker_app/learning/text_quality_validator.py` and `tracker_app/tracking/quiz_engine.py` and found the following structural flaws:

1. **Heuristic-Only Validation for 4+ Letter Words:**
   In `text_quality_validator.py`, the function `is_plausible_concept` relies entirely on heuristic, structural rules for words longer than 3 letters. It checks:
   - Length limits
   - Vowel ratio bounds (`0.12` to `0.85`)
   - Maximum consecutive consonants (`5`)
   - Repeated character runs (e.g., `aaabbb`)
   
   It enforces a strict dictionary check (`_THREE_LETTER_WORDS`) **only for 3-letter words**. Any string of 4 or more letters that happens to have a balanced vowel-to-consonant ratio (like `aastha`, `aearee`, `pebeoge`) perfectly satisfies these constraints and bypasses the filter.

2. **Graph Ingestion (`knowledge_graph.py`):**
   When `sync_db_to_graph` and `add_concepts` are called, these validated (but actually garbage) concepts are added as nodes to the graph. Because they are processed through the `SentenceTransformer` or spaCy vectors, they get embeddings. Since OCR noise often co-occurs with real concepts in the same window, they gain semantic edges (weights) with legitimate nodes.

3. **Micro-Quiz Distractor Logic (`quiz_engine.py`):**
   In `generate_micro_quiz()`, the engine builds distractors by picking the nearest neighbors from the graph (`graph.neighbors(concept_name)`). Because the gibberish strings were captured in the same session as the actual concepts, they are strongly connected in the graph and get pulled in as "hard distractors."

---

## 3. How It Can Be Improved & What Should Be Done

To fix this, we need to move away from purely structural heuristics to semantic and dictionary-based validation.

### Technical Action Plan

**1. Implement a Dictionary-Based Gate for Single Words:**
   Update `text_quality_validator.py` to use an English dictionary (e.g., `nltk.corpus.words` or `pyenchant`) to validate all standalone single-word concepts, not just 3-letter ones. If a single word is not in the dictionary, it should be rejected unless it matches a known whitelist of technical terms (e.g., `pytorch`, `sql`).

**2. N-Gram or Subword Probability Filtering:**
   Because technical terms might not be in standard dictionaries, we can calculate the character n-gram probability of a word. Gibberish strings like `aplaseascrt` or `pebeoge` often have very low trigram probabilities in standard English/Tech text. Reject strings below a certain probability threshold.

**3. Leverage Existing Embeddings for Outlier Detection:**
   Since the app already loads a `SentenceTransformer`, we can compute the distance of newly extracted concepts to a baseline "noise" cluster. If a string maps closely to known OCR noise embeddings, drop it.

**4. Enhance Quiz Distractor Quality:**
   Update `generate_micro_quiz` to ensure that distractors are not just any neighboring node, but rather nodes that have crossed a promotion threshold (e.g., exist in the `LearningItem` deck, or have a `frequency_count >= 3`).

---

## 4. Proposed Improvisations (Advanced Features)

Beyond fixing the bug, here are technical improvisations to make the extraction and quizzing pipeline state-of-the-art:

1. **LLM-Based Concept Extraction (Local/Edge):**
   Instead of parsing raw OCR text with regex and heuristics, feed the raw OCR chunk into a small local LLM (e.g., Llama.cpp or an ONNX model) with the prompt: *"Extract 3 key study concepts from this text. Output only a JSON list."* This shifts the burden of deduplication and noise-filtering to semantic AI.
   
2. **Confidence-Weighted Edges in Knowledge Graph:**
   Right now, edge weight is pure cosine similarity of the embeddings. We should multiply this by the text extraction quality score. A node derived from low-confidence OCR should have very weak semantic pull, preventing it from showing up in quizzes.
   
3. **User-Feedback Loop on Quizzes:**
   Add a small "Report Bad Question/Option" flag on the Micro-Quiz UI. If a user clicks it, the distractor is added to a local `_OCR_NOISE` blocklist and instantly pruned from the knowledge graph and database, effectively crowdsourcing the noise filter.
