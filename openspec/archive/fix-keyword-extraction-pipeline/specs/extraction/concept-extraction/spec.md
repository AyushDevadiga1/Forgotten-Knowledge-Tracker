## Purpose

Extracts study-relevant concepts from captured text (OCR screenshots, browser content) using grammar-aware NLP extraction instead of statistical keyword co-occurrence, producing semantically meaningful keywords for the spaced repetition system.

## ADDED Requirements

### Requirement: spaCy-first extraction
The system SHALL use spaCy noun chunks and named entity recognition as the primary extraction method. YAKE statistical extraction SHALL be used only as a supplementary signal for phrases spaCy misses.

#### Scenario: Extract concepts from study text
- **WHEN** text containing study material is submitted for extraction (e.g., "Photosynthesis converts light energy into chemical energy using chlorophyll")
- **THEN** the system extracts noun chunks ("photosynthesis", "light energy", "chemical energy", "chlorophyll") as primary keywords with confidence 0.7

#### Scenario: spaCy extracts named entities
- **WHEN** text contains named entities of type PRODUCT, EVENT, WORK_OF_ART, LAW, or LANGUAGE
- **THEN** the system extracts them as keywords with confidence 0.8

#### Scenario: YAKE supplements spaCy
- **WHEN** spaCy extraction produces fewer than 5 keywords
- **THEN** YAKE-extracted phrases are added as supplementary keywords with confidence 0.5

### Requirement: Selective entity filtering
The system SHALL block PERSON entity names from becoming keywords (via the existing `_BLOCKED_NAMES` list) but SHALL allow ORG and GPE entities as study-relevant concepts (e.g., "Stanford University", "United States", "Microsoft").

#### Scenario: Person names are blocked
- **WHEN** text contains "John Smith works at Stanford University"
- **THEN** "john" and "smith" are NOT extracted as keywords, but "stanford university" IS extracted

#### Scenario: Organizations are allowed
- **WHEN** text mentions "Google published a paper on transformer architecture"
- **THEN** "google" IS extracted as a keyword (study-relevant organization)

#### Scenario: Locations are allowed
- **WHEN** text discusses "The French Revolution began in Paris, France"
- **THEN** "france" and "paris" ARE extracted as keywords (study-relevant locations)

### Requirement: POS-based bigram filtering
The system SHALL reject YAKE-extracted bigrams that cross grammatical boundaries. Bigrams containing a verb as either the first or second word SHALL be rejected unless both words are nouns or proper nouns.

#### Scenario: Verb+noun bigram rejected
- **WHEN** YAKE produces "developing machine" (verb + noun)
- **THEN** this bigram is rejected and not returned as a keyword

#### Scenario: Name+verb bigram rejected
- **WHEN** YAKE produces "smith works" (proper noun + verb)
- **THEN** this bigram is rejected and not returned as a keyword

#### Scenario: Noun+noun bigram kept
- **WHEN** YAKE produces "neural network" (noun + noun)
- **THEN** this bigram is kept and returned as a keyword

#### Scenario: Adjective+noun bigram kept
- **WHEN** YAKE produces "machine learning" (noun/adjective + noun)
- **THEN** this bigram is kept and returned as a keyword

### Requirement: Study-term whitelist for quality filter
The system SHALL maintain a whitelist of legitimate study terms that bypass the trigram coverage and dictionary quality checks. Terms in this whitelist SHALL be accepted by `is_plausible_concept()` regardless of their trigram coverage score.

#### Scenario: Rare CS terms accepted
- **WHEN** text contains "monad" or "functor" or "applicative"
- **THEN** these terms pass the quality filter and are extractable as keywords

#### Scenario: Brand names accepted
- **WHEN** text contains "Bitcoin" or "Ethereum" or "Python" or "JavaScript"
- **THEN** these terms pass the quality filter and are extractable as keywords

#### Scenario: Rare English words accepted
- **WHEN** text contains "defenestration" or "sesquipedalian" or "quixotic"
- **THEN** these terms pass the quality filter (they are real English words)

### Requirement: Unified extraction path
The system SHALL use a single `extract_concepts()` function for both OCR and browser ingestion paths. Both paths SHALL produce identical extraction behavior for the same input text.

#### Scenario: OCR and browser paths agree
- **WHEN** the same text is submitted via OCR capture and browser extension
- **THEN** both paths produce the same set of keywords with the same scores

#### Scenario: Single entry point
- **WHEN** either OCR or browser path needs keyword extraction
- **THEN** both call `extract_concepts(text)` from `keyword_extractor.py`

### Requirement: Confidence scoring tiers
The system SHALL assign confidence scores using three tiers: spaCy named entities at 0.8, spaCy noun chunks at 0.7, and YAKE supplementary phrases at 0.5. When the same keyword appears from multiple sources, the highest score wins.

#### Scenario: Entity gets highest score
- **WHEN** "neural network" appears as both a noun chunk and a YAKE phrase
- **THEN** the final score is 0.7 (noun chunk score, higher than YAKE's 0.5)

#### Scenario: Entity type gets priority
- **WHEN** "transformer" appears as a PRODUCT entity and a noun chunk
- **THEN** the final score is 0.8 (entity score, higher than noun chunk's 0.7)
