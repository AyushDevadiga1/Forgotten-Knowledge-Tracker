## Why

FKT's keyword extraction pipeline produces broken, semantically meaningless keywords from study text. YAKE (the statistical keyword extractor) generates bigrams like "smith works" and "microsoft developing" instead of actual study concepts. This is because YAKE measures statistical co-occurrence without understanding grammar or entities. The quality filter compounds the problem by rejecting legitimate rare study terms ("monad", "functor", "Bitcoin") while letting YAKE garbage through. The OCR and browser extraction paths also use inconsistent logic, producing different results for the same text.

## What Changes

- **BREAKING**: Flip extraction priority from YAKE-primary to spaCy-primary (noun chunks + NER), with YAKE as supplementary signal only
- **BREAKING**: Replace entity blocking (all PERSON/ORG/GPE) with selective filtering (block PERSON names, allow ORG/GPE as study concepts)
- Add POS-based bigram filtering to reject YAKE outputs that cross grammatical boundaries (verb+noun, name+verb)
- Add study-term whitelist to quality filter for legitimate rare words that fail trigram/dictionary checks
- Unify OCR and browser extraction paths into single `extract_concepts()` function
- Add confidence scoring tiers: spaCy entities (0.8) > spaCy noun chunks (0.7) > YAKE phrases (0.5)

## Capabilities

### New Capabilities
- `extraction/concept-extraction`: Core concept extraction pipeline — spaCy-first extraction with YAKE supplement, POS-based filtering, unified OCR/browser paths

### Modified Capabilities
None — this is a quality fix, not a behavior change for callers.

## Impact

- `tracker_app/tracking/keyword_extractor.py`: Major refactor — spaCy becomes primary, YAKE becomes supplementary, add POS filtering
- `tracker_app/tracking/ocr_module.py`: Replace dual extraction logic with unified `extract_concepts()` call
- `tracker_app/web/api.py`: Use unified extraction instead of separate YAKE-only path
- `tracker_app/learning/text_quality_validator.py`: Add study-term whitelist, relax quality gate for spaCy-validated words
- `tracker_app/tracking/privacy_filter.py`: Minor — entity filtering adjustments
