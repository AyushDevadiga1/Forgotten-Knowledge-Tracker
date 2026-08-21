# FKT Extraction Pipeline — Complete Analysis

## Overview

FKT is a passive learning tracker. It captures what you study (via OCR, audio, webcam), extracts keywords/concepts, schedules them for spaced repetition review, and builds a knowledge graph.

```
+--------------+    +--------------+    +--------------+
¦   Screenshot ¦    ¦    Audio     ¦    ¦    Webcam    ¦
¦   (OCR)      ¦    ¦  (classify)  ¦    ¦  (attention) ¦
+--------------+    +--------------+    +--------------+
       ¦                   ¦                   ¦
       ?                   ?                   ?
+--------------+    +--------------+    +--------------+
¦  Tesseract   ¦    ¦  MFCC +      ¦    ¦  EAR +       ¦
¦  OCR Text    ¦    ¦  classify    ¦    ¦  MediaPipe   ¦
+--------------+    +--------------+    +--------------+
       ¦                   ¦                   ¦
       ?                   ¦                   ¦
+--------------+           ¦                   ¦
¦   Privacy    ¦           ¦                   ¦
¦   Filter     ¦           ¦                   ¦
+--------------+           ¦                   ¦
       ¦                   ¦                   ¦
       ?                   ¦                   ¦
+--------------+           ¦                   ¦
¦   Text       ¦           ¦                   ¦
¦   Quality    ¦           ¦                   ¦
+--------------+           ¦                   ¦
       ¦                   ¦                   ¦
       ?                   ¦                   ¦
+--------------+           ¦                   ¦
¦   Keyword    ¦           ¦                   ¦
¦   Extract    ¦           ¦                   ¦
+--------------+           ¦                   ¦
       ¦                   ¦                   ¦
       ?                   ?                   ?
+--------------------------------------------------+
¦              Intent Classification               ¦
¦         (only "studying" cycles pass)            ¦
+--------------------------------------------------+
                       ¦
                       ?
+--------------------------------------------------+
¦           Concept Scheduler (SM-2 + AWFC)        ¦
¦     Frequency = 3 ? auto-promote to deck         ¦
+--------------------------------------------------+
                       ¦
                       ?
+--------------------------------------------------+
¦        Knowledge Graph (SentenceTransformer)     ¦
¦       Cosine > 0.7 ? edge between concepts       ¦
+--------------------------------------------------+
```

## Capture Sources

### 1. OCR Module (Primary)
**File:** `tracker_app/tracking/ocr_module.py`
**Entry:** `ocr_pipeline()` (line 362)

Flow:
1. `capture_screenshot()` (line 93) — grabs screen or ROI via mss
2. Deduplication via MD5 of 192×108 thumbnail (line 116) — skip if identical to last
3. `capture_active_window()` (line 66) — gets window title
4. `is_sensitive_window(title)` — skip banking/medical/etc.
5. `preprocess_image()` (line 149) — grayscale, threshold, denoise
6. `extract_text()` (line 178) — Tesseract OCR, `--oem 3 --psm 6`, min confidence 30
7. `extract_keywords()` (line 227) — YAKE + spaCy + knowledge graph boost
8. Raw text truncated to 500 chars for storage (line 400)

Config (env overrides):
- `SCREENSHOT_INTERVAL = 20s`
- `OCR_MIN_WORD_CONFIDENCE = 30`

### 2. Audio Module (Intent Only)
**File:** `tracker_app/tracking/audio_module.py`
**Entry:** `audio_pipeline_async(callback)` (line 163)

Does NOT extract concepts. Classifies ambient audio:
- 5-second recordings at 22050 Hz
- MFCC feature extraction (line 35)
- Energy-based classification: silence/music/speech/unknown (line 91)
- Feeds into intent classifier ? only "studying" cycles produce concepts

### 3. Webcam Module (Attention Only)
**File:** `tracker_app/tracking/webcam_module.py`
**Entry:** `webcam_pipeline(num_frames=3)` (line 210)

Does NOT extract concepts. Measures attention:
- MediaPipe FaceMesh for eye landmarks
- Eye Aspect Ratio (EAR) calculation (line 42)
- Attention score 0–100 (line 131)
- 30-second calibration on first run (line 65)

### 4. Browser Extension Ingest
**File:** `tracker_app/web/api.py`
**Endpoint:** `POST /api/v1/ingest` ? `browser_ingest()` (line 688)

Alternative to OCR. Receives text directly from browser extension:
- Title sanitization (line 61)
- Privacy gate via `sanitize_text_for_storage()` (line 724)
- Text quality validation (line 730)
- Keyword extraction via `get_keyword_scores_dict()` (line 736)
- Concept scheduling for each keyword (line 748)
- Hardcoded `attention_at_encoding=60.0` (line 752)
- Max text: 10,000 chars, min text: 20 chars

## Privacy Filter

**File:** `tracker_app/tracking/privacy_filter.py`

### Window Title Gate
`is_sensitive_window()` (line 148) — substring match against:
password, login, sign in, authentication, bank, paypal, credit card, payment, private, incognito, inprivate, medical, health, prescription

### Text Sanitization
`sanitize_text_for_storage()` (line 125) — regex detection of:
- Credit cards (16-digit), Amex, Discover
- SSN (dashed and bare)
- Email, phone numbers
- Bank accounts, IBAN
- Passwords, API keys, IP addresses
- Dates of birth

Threshold: >3 redactions ? entire capture rejected (`safe_to_store=False`)

### Redaction Marker Stripping
`strip_redaction_markers()` (line 180) — removes `[REDACTED:TYPE]` markers before keyword extraction

### Sensitive Keyword Filtering
`filter_sensitive_keywords()` (line 191) — drops:
- `SENSITIVE_KEYWORD_NOISE`: redacted, email, phone, ssn, card, password, etc.
- `_COMMON_NAMES`: ~200 first/last names
- Keywords containing `@`
- Pure numeric/phone-like strings
- Keywords matching sensitive data patterns

Defense-in-depth: also called at `ConceptScheduler.add_concept()` (concept_scheduler.py:46)

## Text Quality Validation

**File:** `tracker_app/learning/text_quality_validator.py`

### Pipeline
1. Empty/length check (line 797)
2. `preprocess_ocr_text()` (line 544):
   - OCR error corrections (`l0`?`10`, `O0`?`00`)
   - Whitespace normalization, control char removal
   - Mixed case bonus (+0.1 quality)
   - Length: min 3, max 500 chars
3. `is_coherent_text()` (line 495):
   - No control chars
   - No garbage patterns (special chars only, long numbers, IPs)
   - Vowel ratio = 15% for text > 5 chars
   - Word diversity = 0.3 for > 10 words
   - = 30% recognizable words
4. `calculate_text_quality_score()` (line 643):
   - Base 0.3, adjusted by length, character validity, coherence, UI garbage, diversity
   - UI_GARBAGE blocklist (~100 terms) ? score 0.05 (auto-reject)
5. Decision: `is_useful = quality_score = 0.4 AND len(keywords) > 0`

### Concept Plausibility Gate
`is_plausible_concept(text)` (line 253) — called per keyword:
1. Length 3–80 chars
2. Not in `_STOPWORD_CONCEPTS` (~30 stopwords)
3. Not in `_UI_ELEMENT_BLOCKLIST` (~130 browser/OS/code terms)
4. Per-token validation via `_is_plausible_token()`:
   - Fragment blocklist (~40 OCR artifacts)
   - OCR noise blocklist (~80 live misreads)
   - Phrase connectors allowed in multi-word phrases
5. `_is_plausible_word()`:
   - Acronym whitelist (SQL, CSS, HTML, API, etc.)
   - 3-letter word whitelist (~300 words)
   - Vowel/consonant requirements
   - Max token length: 20
   - Max consecutive consonants: 5
   - Vowel ratio: 0.12–0.85
   - Repeated character run detection
   - English dictionary gate for words = 5 letters:
     - Must be in `english_words.txt` (~2808 words) OR
     - Pass structural analysis: dominant letter check, compound stems, suffix root length, trigram coverage = 30%
   - 4-letter non-dictionary words rejected

## Keyword Extraction

**File:** `tracker_app/tracking/keyword_extractor.py`

### Three Pipelines (merged):

#### YAKE! (line 176–195)
- `yake.KeywordExtractor(lan="en", n=2, dedupLim=0.7, dedupFunc="seqm", windowsSize=2, top=20)`
- Scores inverted (lower YAKE = more relevant ? 0–1 relevance)
- `YAKE_SCORE_CAP = 0.5` — scores above this discarded
- `MIN_KW_LEN = 3`

#### spaCy NER + Noun Chunks (line 197–228)
- Model: `en_core_web_sm`
- Accepted entity types: `PRODUCT`, `EVENT`, `WORK_OF_ART`, `LAW`, `LANGUAGE`
- Blocked entity types: `PERSON`, `ORG`, `GPE`, `NORP`, `FAC`, `LOC`
- Entity score floor: 0.7
- Noun chunk score floor: 0.35
- Individual noun/propn token score floor: 0.25
- Text capped at 50,000 chars for performance

#### Frequency Fallback (line 246–256)
- Used only if both YAKE and spaCy fail
- Normalized word frequency for 3+ letter non-stopwords

### Post-Extraction Filtering
- Weak phrase filter: drops multi-word keywords containing verbs/function words from `WEAK_PHRASE_TOKENS` (~20 words)
- Personal name filter: drops keywords where ALL words are in `_BLOCKED_NAMES` (~290 names)
- Blocked entity text filter: drops ORG/GPE entity texts

### Scoring (in ocr_module.py:227)
After YAKE, additional scoring:
1. TF-IDF keywords: `score * 0.8`
2. spaCy nouns/entities: `score = 0.3`
3. camelCase/snake_case splitting (line 304–325)
4. Repetition boost: `+0.05 * (count - 1)`
5. Knowledge graph boost: `+0.1` if already in graph
6. Final sort, top 15, then `filter_sensitive_keywords()`

## Concept Scheduling

**File:** `tracker_app/learning/concept_scheduler.py`

### Entry: `add_concept(concept, confidence, context, attention_at_encoding, source)` (line 24)

### Pre-Storage Gates
1. `filter_sensitive_keywords()` — defense-in-depth
2. `is_plausible_concept()` — quality gate

### New Concept
```python
TrackedConcept(
    concept=concept,           # PK: the concept string
    first_seen=now,
    last_seen=now,
    next_review=now,           # Due immediately
    relevance_score=confidence,
    attention_at_encoding=attention_at_encoding,
    lambda_personalised=compute_awfc_lambda(DEFAULT_LAMBDA, attention_at_encoding),
)
```

### Existing Concept Update
- Attention EMA: `0.8 * old + 0.2 * new`
- Lambda: gentle nudge `0.9 * old + 0.1 * attention_lambda` (after 1+ reviews)
- Frequency: +1
- Relevance: rolling average `(old + confidence) / 2.0`
- Auto-promote at `frequency_count == 3` AND `is_kb_worthy()`

### Encounter Logging
Every call creates `ConceptEncounter`: concept, timestamp, source, confidence, context[:200]

### SM-2 Review Scheduling
`schedule_next_review(concept_id, quality=3)` (line 149):
- Ease factor bounds: [1.3, 3.5]
- Ease delta: `0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)`
- Second review: 3 days
- Subsequent: `interval * new_ease`

### AWFC (Attention-Weighted Forgetting Curve)
**File:** `tracker_app/learning/memory_model.py`
- `lambda_p = base_lambda * (1 - attention_norm * 0.30)`
- `R(t) = exp(-lambda_p * t_hours)`
- Clamps: lambda [0.01, 0.50], retention [0.05, 1.0]

## Concept Promotion

**File:** `tracker_app/learning/concept_promotion.py`

### Auto-Promotion
- Trigger: `frequency_count == PROMOTE_AFTER_ENCOUNTERS (3)`
- KB-worthiness gate: not in `UI_CHROME` set, or in curated exceptions, or passes `is_plausible_concept()`
- Subsumption check: single-word concepts covered by tracked multi-word phrases are not promoted
- Creates `LearningItem` with difficulty mapped from relevance score

## Knowledge Graph

**File:** `tracker_app/tracking/knowledge_graph.py`

- Library: NetworkX undirected graph
- Persistence: pickle file at `DATA_DIR/knowledge_graph.pkl`
- Max nodes: 5,000 (eviction of lowest-memory zero-edge nodes)
- Embedding: `SentenceTransformer('all-MiniLM-L6-v2')` with spaCy fallback
- Edge creation: cosine similarity > 0.7
- Edge weight: EMA `0.85 * old + 0.15 * cosine_sim`
- Sync: `sync_db_to_graph()` every 60s (incremental)

### Node Attributes
```python
{
    "embedding": List[float],
    "count": int,
    "memory_score": float,      # AWFC retention [0.05, 1.0]
    "next_review_time": str,
    "last_review": str,
    "intent_conf": float,       # 1.0
}
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/ingest` | POST | Browser extension text ingest |
| `/api/v1/items` | POST | Manual learning item creation |
| `/api/v1/items/backfill` | POST | Concept?deck migration |
| `/api/v1/reviews` | POST | SM-2 review recording |
| `/api/v1/quiz/answer` | POST | Quiz result ? SM-2 |
| `/api/v1/intent/feedback` | POST | User feedback on intent |
| `/api/v1/graph/sync` | POST | Force graph rebuild |
| `/api/v1/session/start` | POST | Toggle session on |
| `/api/v1/session/stop` | POST | Toggle session off |
| `/api/v1/concepts/<concept>` | DELETE | Right-to-be-forgotten |
| `/api/v1/tracking/history` | DELETE | Clear passive capture trail |

## Database Schema (Key Tables)

### tracked_concepts
| Column | Type | Default | Notes |
|--------|------|---------|-------|
| concept | String (PK) | — | Concept string |
| first_seen | DateTime | utcnow | |
| last_seen | DateTime | utcnow | Indexed |
| frequency_count | Integer | 1 | Encounters |
| relevance_score | Float | 0.5 | Rolling average |
| status | String | "discovered" | |
| interval | Integer | 1 | SM-2 days |
| memory_strength | Float | 2.5 | SM-2 ease |
| next_review | DateTime | — | Indexed |
| repetitions | Integer | 0 | Consecutive successes |
| attention_at_encoding | Float | 50.0 | 0–100 |
| lambda_personalised | Float | 0.1 | AWFC decay |

### concept_encounters
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | Auto |
| concept | String (FK) | CASCADE delete |
| timestamp | DateTime | Indexed |
| source | String | ocr/browser_extension/manual |
| confidence | Float | |
| context_snippet | String | Max 200 chars |

### learning_items (deck)
| Column | Type | Notes |
|--------|------|-------|
| id | String (PK) | UUID |
| question | String | The concept |
| answer | String | Auto-generated |
| difficulty | String | easy/medium/hard |
| interval | Integer | SM-2 |
| ease_factor | Float | 2.5 default |
| next_review_date | DateTime | Indexed |
| status | String | active/mastered/archived |

---

## Suspicious Activities & Security Issues

### CRITICAL

1. **Pickle deserialization (RCE risk)** — `knowledge_graph.py:130`
   `pickle.load()` on `knowledge_graph.pkl` is inherently unsafe. If the pkl file is tampered with (e.g., via a compromised download or shared config), arbitrary Python code executes on load.
   **Impact:** Remote code execution if pkl file is attacker-controlled.
   **Fix:** Replace pickle with a safe format (JSON, msgpack, or sqlite-backed storage).

2. **No authentication on API endpoints** — `api.py` (all endpoints)
   Any process on localhost can POST to `/api/v1/ingest`, inject arbitrary concepts, trigger retraining, or DELETE all data. The API key check exists but is disabled by default (`API_KEY` defaults to empty string in config.py).
   **Impact:** Local privilege escalation, data injection, data destruction.
   **Fix:** Require API key by default; add rate limiting.

3. **Hardcoded SECRET_KEY** — `config.py`
   Flask `SECRET_KEY` defaults to `'dev-secret-key-change-in-production'`. Session cookies are trivially forgeable.
   **Impact:** Session hijacking if exposed to network.
   **Fix:** Generate random key on first run, store in `.env`.

### HIGH

4. **SQL injection risk in raw queries** — `knowledge_graph.py:416-450`
   `fetch_concepts_from_db()` uses raw `sqlite3.execute()` with string formatting in some code paths. Parameterized queries are used in most places, but the raw sqlite3 fallback path has inconsistent parameterization.
   **Impact:** Potential SQL injection if user-controlled data reaches raw queries.

5. **CORS wildcard** — `api.py`
   `Access-Control-Allow-Origin: *` allows any website to make cross-origin requests to the local API.
   **Impact:** Malicious webpage could read study data or inject concepts via browser extension path.

6. **Pickle in session cookies** — `api.py`
   Flask sessions use `SECRET_KEY` for signing. With a weak/hardcoded key, sessions can be forged.
   **Impact:** Session manipulation.

### MEDIUM

7. **Hardcoded attention for browser ingest** — `api.py:752`
   `attention_at_encoding=60.0` is fixed for all browser ingest regardless of actual user engagement. This skews AWFC decay calculations.
   **Impact:** Inaccurate memory model for browser-ingested concepts.

8. **Concept primary key is case-sensitive string** — `models.py:251`
   `"Photosynthesis"` and `"photosynthesis"` are different concepts. YAKE may produce mixed-case output.
   **Impact:** Duplicate concepts in database.

9. **Text truncation without notice** — `ocr_module.py:400`, `api.py:703`
   OCR text truncated to 500 chars, browser ingest to 10,000 chars. Keywords from truncated portion are lost silently.
   **Impact:** Data loss for long study passages.

10. **spaCy model not in requirements.txt** — `keyword_extractor.py`
    `en_core_web_sm` is loaded at module import. If not installed, extraction silently degrades.
    **Impact:** Reduced extraction quality without user awareness.

11. **Race conditions in concept updates** — `concept_scheduler.py:63-113`
    Multiple concurrent OCR cycles can read-modify-write the same concept row without locking.
    **Impact:** Lost updates, inconsistent frequency counts.

12. **SSN regex false positive** — `privacy_filter.py:16`
    `ssn_digits` pattern matches any 9-digit sequence, causing legitimate study content to be redacted.
    **Impact:** False redaction of numerical study material.

13. **Adaptive throttling can starve OCR** — `loop.py:149`
    At >70% CPU, OCR interval scales to 2.5×. During heavy compilation/scientific workloads, the system may effectively stop tracking.
    **Impact:** Missing study content during peak CPU usage.

### LOW

14. **Dead code paths** — various
    `webcam_module.py` has unused calibration functions. `audio_module.py` has unused MFCC visualization code.

15. **Swallowed exceptions** — `ocr_module.py:26-37`
    Tesseract-not-found silently returns empty text with only a warning log. No user-facing indication.

16. **Inconsistent spaCy text caps** — `ocr_module.py:281` (100,000) vs `keyword_extractor.py:202` (50,000)
    Two different limits for the same pipeline.

17. **Deprecated datetime usage in tests** — test files
    Multiple test files use `datetime.utcnow()` (deprecated), producing warnings.

18. **Debug print statements** — `concept_scheduler.py`, `activity_monitor.py`
    Several `print()` statements left in production code for debugging.

---

## Recommendations (Priority Order)

1. **Replace pickle** with JSON or sqlite-backed knowledge graph storage
2. **Enforce API key** by default; add localhost-only restriction
3. **Generate random SECRET_KEY** on first run
4. **Fix CORS** to localhost-only or configurable origin
5. **Case-normalize concept keys** before DB insert
6. **Add row-level locking** for concept updates
7. **Report truncation** to caller (return flag indicating data loss)
8. **Add spaCy model check** at startup with user-facing warning
9. **Tighten SSN regex** to reduce false positives
10. **Remove debug print() statements** from production code
