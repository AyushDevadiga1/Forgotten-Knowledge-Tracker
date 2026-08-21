## 1. Quality Filter Whitelist

- [x] 1.1 Add `_STUDY_TERM_WHITELIST` frozenset to `text_quality_validator.py` with rare study terms (monad, functor, applicative, Bitcoin, Ethereum, Python, JavaScript, defenestration, sesquipedalian, quixotic, etc.)
- [x] 1.2 Modify `_is_plausible_word()` to check whitelist before trigram/dictionary gates
- [x] 1.3 Add tests for whitelist terms passing quality filter

## 2. Entity Filtering

- [x] 2.1 Update `BLOCKED_ENTITY_TYPES` in `keyword_extractor.py` to only block PERSON (remove ORG, GPE, NORP, FAC, LOC from blocked set)
- [x] 2.2 Verify `filter_sensitive_keywords()` in `privacy_filter.py` still catches PII from allowed entity types
- [x] 2.3 Add tests for ORG/GPE extraction (e.g., "Stanford University" → extracted, "John Smith" → blocked)

## 3. POS-Based Bigram Filtering

- [x] 3.1 Add `_is_verb_containing_bigram()` helper to `keyword_extractor.py` using spaCy POS tags
- [x] 3.2 Apply POS filter to YAKE bigrams in `extract_keywords()` method
- [x] 3.3 Add tests for verb+noun rejection ("developing machine" → rejected, "neural network" → kept)

## 4. Unified Extraction Function

- [x] 4.1 Create `extract_concepts(text, top_n=15)` function in `keyword_extractor.py` with spaCy-first + YAKE-supplementary pipeline
- [x] 4.2 Implement confidence tiers: entities 0.8, noun chunks 0.7, YAKE 0.5
- [x] 4.3 Implement YAKE fallback: only use YAKE when spaCy produces < 5 keywords
- [x] 4.4 Update `ocr_module.extract_keywords()` to call `extract_concepts()` instead of separate YAKE + spaCy logic
- [x] 4.5 Update `api.py` browser_ingest to call `extract_concepts()` instead of `get_keyword_scores_dict()`
- [x] 4.6 Remove duplicate spaCy extraction logic from `ocr_module.py`

## 5. Testing & Verification

- [x] 5.1 Run full test suite (370+ tests should pass, 1 pre-existing failure)
- [x] 5.2 Run pipeline simulation with dummy words (same test from explore mode) and verify improved results
- [x] 5.3 Verify no regressions in concept scheduling (add_concept still receives valid keywords)
- [x] 5.4 Run lint/typecheck if available
