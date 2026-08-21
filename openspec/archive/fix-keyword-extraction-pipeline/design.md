## Context

The extraction pipeline currently has two independent implementations:
1. `keyword_extractor.py` — YAKE + spaCy (used by browser API)
2. `ocr_module.py` — YAKE + separate spaCy extraction (used by OCR path)

YAKE is the primary extractor in both paths, producing statistically-ranked keyword phrases. spaCy is secondary, adding noun chunks and entities at lower confidence. The quality filter (`text_quality_validator.py`) gates all output using trigram coverage and dictionary checks designed for OCR gibberish.

The core problem: YAKE doesn't understand grammar. It produces bigrams like "smith works" (name+verb) and "microsoft developing" (org+verb) that are statistically unusual but semantically meaningless. Meanwhile, legitimate study terms ("monad", "Bitcoin") fail the quality filter because they're rare in the trigram dictionary.

## Goals / Non-Goals

**Goals:**
- Make spaCy the primary extractor (noun chunks at 0.7, entities at 0.8)
- Make YAKE supplementary only (phrases at 0.5, used when spaCy produces < 5 keywords)
- Block person names but allow ORG/GPE entities as study concepts
- Reject YAKE bigrams that cross POS boundaries (verb+noun, name+verb)
- Allow legitimate study terms through the quality filter via a whitelist
- Unify OCR and browser paths into single `extract_concepts()` function

**Non-Goals:**
- Replace YAKE entirely (it still provides value for multi-word phrases spaCy misses)
- Change the downstream concept scheduler or knowledge graph (extraction only)
- Add new NLP models or external dependencies
- Change the privacy filter behavior (already working correctly)

## Decisions

### Decision 1: spaCy-first, YAKE-supplementary

**Choice:** Use spaCy noun chunks and NER as primary extraction (confidence 0.7-0.8), YAKE as fallback only when spaCy produces < 5 keywords (confidence 0.5).

**Alternatives considered:**
- YAKE-only: Rejected — produces semantically meaningless bigrams
- spaCy-only: Rejected — misses some multi-word phrases YAKE catches well
- Ensemble (average scores): Rejected — YAKE garbage dilutes spaCy quality

**Rationale:** spaCy understands grammar and entities. For a learning system, grammatically valid concepts are more valuable than statistically interesting word combinations. YAKE still has value for phrases like "light energy" or "data science" that spaCy might split into individual nouns.

### Decision 2: Selective entity filtering (not all-or-nothing)

**Choice:** Block PERSON entities via `_BLOCKED_NAMES` list. Allow ORG, GPE, NORP, LOC entities as study concepts.

**Alternatives considered:**
- Block all entities (current approach): Rejected — loses "Stanford University", "United States"
- Allow all entities: Rejected — PII risk from person names
- Whitelist specific ORGs: Rejected — too maintenance-heavy, new orgs appear constantly

**Rationale:** The `_BLOCKED_NAMES` list (290 first/last names) is sufficient to block PII. Organizations and locations are legitimate study concepts. The existing `filter_sensitive_keywords` in `privacy_filter.py` provides a second safety net.

### Decision 3: POS-based bigram filtering using spaCy POS tags

**Choice:** After YAKE produces bigrams, use spaCy POS tags to reject bigrams where either word is a verb (unless both are nouns/proper nouns).

**Alternatives considered:**
- Keep all YAKE bigrams: Rejected — "smith works", "developing machine" are noise
- Reject all multi-word YAKE: Rejected — loses good phrases like "neural network"
- Use YAKE's own scoring only: Rejected — YAKE scores "smith works" higher than "neural network"

**Rationale:** spaCy already provides POS tags. Adding a simple check (reject if either word is VERB, AUX) costs almost nothing and eliminates the worst YAKE garbage.

### Decision 4: Study-term whitelist in quality filter

**Choice:** Add a `_STUDY_TERM_WHITELIST` frozenset to `text_quality_validator.py` containing legitimate rare study terms. Terms in this whitelist bypass the trigram coverage and dictionary checks in `is_plausible_concept()`.

**Alternatives considered:**
- Lower trigram threshold (30% → 20%): Rejected — lets more gibberish through
- Remove trigram check entirely: Rejected — breaks gibberish detection
- Use POS tag to bypass quality: Rejected — POS tags are available at extraction time, not quality gate time

**Rationale:** The whitelist is explicit, auditable, and doesn't weaken the quality filter for unknown words. It only lets through known study terms that we've verified are legitimate.

### Decision 5: Unified `extract_concepts()` function

**Choice:** Create a single `extract_concepts(text, top_n=15)` function in `keyword_extractor.py` that both OCR and browser paths call. This function encapsulates the full spaCy-first + YAKE-supplementary pipeline.

**Alternatives considered:**
- Keep separate implementations: Rejected — inconsistent behavior, duplicated logic
- Create new module: Rejected — adds complexity, keyword_extractor.py is the right home
- Make it a class method: Rejected — stateless function is simpler

**Rationale:** Single source of truth for extraction behavior. Both paths get identical results. Easier to test and maintain.

## Risks / Trade-offs

**[Risk] spaCy is slower than YAKE** → Mitigated by: spaCy already loaded for NER in OCR path; text capped at 50K chars; only runs once per extraction call.

**[Risk] YAKE supplementary may still produce garbage** → Mitigated by: POS filtering rejects verb-containing bigrams; quality filter still gates all output; confidence 0.5 means YAKE output ranks below spaCy output.

**[Risk] Study-term whitelist may need ongoing maintenance** → Mitigated by: whitelist is small (20-30 terms), explicit, and only blocks legitimate rare terms. New terms can be added as discovered.

**[Risk] Breaking change for callers expecting YAKE-style output** → Mitigated by: `extract_concepts()` returns same format as current `extract_keywords()`; downstream `filter_sensitive_keywords()` and `add_concept()` unchanged.

**[Risk] ORG/GPE extraction may introduce noise** → Mitigated by: existing `filter_sensitive_keywords()` still runs; only entities spaCy confidently identifies (not all words) are extracted; confidence 0.8 means they rank high but still go through quality gate.
