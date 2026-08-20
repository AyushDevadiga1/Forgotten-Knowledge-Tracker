"""Keyword extractor -- YAKE! ranking with spaCy NER and noun-chunk supplementation.

Replaces the broken TF-IDF single-document extractor with YAKE!
(Yet Another Keyword Extractor) -- a statistical, corpus-free algorithm
that actually ranks keywords by importance within a single document.

Why YAKE! beats TF-IDF here:
  TF-IDF on ONE document gives every term the same score (= 1.0).
  YAKE! uses term frequency, casing, position, co-occurrence, and
  sentence dispersion within the single text -- real ranking without
  needing a background corpus.

Pipeline:
  1. YAKE!          -> ranked keyword candidates (statistical)
  2. spaCy NER      -> named entities (PRODUCT, EVENT)
  3. spaCy nouns    -> noun chunks as supplementary candidates
  4. Merge + dedup  -> final scored keyword dict

Fallback: if YAKE! is not installed, falls back to spaCy noun extraction.
"""

import logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger("KeywordExtractor")

# -- Lazy-loaded heavy objects ----------------------------------------
_yake_extractor = None
_spacy_nlp      = None

def _get_yake():
    """Return the YAKE extractor singleton (lazy init).

    The extractor is created once with FIXED parameters (English, bigram
    window, top 20): YAKE bakes its configuration into the instance at
    construction time, so per-call parameters would be silently ignored
    after the first init (M-10). Callers slice the result to their own top_n.
    """
    global _yake_extractor
    if _yake_extractor is None:
        try:
            import yake
            _yake_extractor = yake.KeywordExtractor(
                lan="en",
                n=2,
                dedupLim=0.7,      # deduplicate near-identical keywords
                dedupFunc="seqm",
                windowsSize=2,
                top=20,
                features=None,
            )
            logger.info("YAKE! keyword extractor initialised.")
        except ImportError:
            logger.warning("YAKE! not installed. Run: pip install yake")
            _yake_extractor = None
    return _yake_extractor

# None = never tried; _SPACY_NLP_FAILED = load failed (stop retrying + log spam)
_SPACY_NLP_FAILED = object()

def _get_nlp():
    """Return spaCy nlp model (lazy init)."""
    global _spacy_nlp
    if _spacy_nlp is _SPACY_NLP_FAILED:
        return None
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm loaded for keyword extraction.")
        except Exception as e:
            logger.warning(f"spaCy load failed: {e}. Will not retry.")
            _spacy_nlp = _SPACY_NLP_FAILED
            return None
    return _spacy_nlp


_BLOCKED_NAMES = frozenset({
    'james', 'john', 'robert', 'michael', 'david', 'william', 'richard',
    'joseph', 'thomas', 'charles', 'christopher', 'daniel', 'matthew',
    'anthony', 'mark', 'donald', 'steven', 'paul', 'andrew', 'joshua',
    'kenneth', 'kevin', 'brian', 'george', 'timothy', 'ronald', 'edward',
    'jason', 'jeffrey', 'ryan', 'jacob', 'gary', 'nicholas', 'eric',
    'jonathan', 'stephen', 'larry', 'justin', 'scott', 'brandon', 'benjamin',
    'samuel', 'raymond', 'gregory', 'frank', 'patrick', 'jack', 'dennis',
    'jerry', 'alexander', 'tyler', 'aaron', 'jose', 'adam', 'nathan',
    'mary', 'patricia', 'jennifer', 'linda', 'barbara', 'elizabeth',
    'susan', 'jessica', 'sarah', 'karen', 'lisa', 'nancy', 'betty',
    'margaret', 'sandra', 'ashley', 'dorothy', 'kimberly', 'emily',
    'donna', 'michelle', 'carol', 'amanda', 'melissa', 'deborah',
    'stephanie', 'rebecca', 'sharon', 'laura', 'cynthia', 'kathleen',
    'amy', 'angela', 'shirley', 'anna', 'brenda', 'pamela', 'emma',
    'nicole', 'helen', 'samantha', 'katherine', 'christine', 'debra',
    'rachel', 'carolyn', 'janet', 'catherine', 'maria', 'heather',
    'diane', 'ruth', 'julie', 'olivia', 'joyce', 'virginia', 'victoria',
    'kelly', 'lauren', 'christina', 'joan', 'evelyn', 'judith', 'megan',
    'andrea', 'cheryl', 'hannah', 'jacqueline', 'martha', 'gloria',
    'teresa', 'ann', 'sara', 'madison', 'frances', 'kathryn', 'janice',
    'jean', 'abigail', 'alice', 'judy', 'sophia', 'grace', 'denise',
    'smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller',
    'davis', 'rodriguez', 'martinez', 'hernandez', 'lopez', 'gonzalez',
    'wilson', 'anderson', 'thomas', 'taylor', 'moore', 'jackson', 'martin',
    'lee', 'perez', 'thompson', 'white', 'harris', 'sanchez', 'clark',
    'ramirez', 'lewis', 'robinson', 'walker', 'young', 'allen', 'king',
    'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores', 'green',
    'adams', 'nelson', 'baker', 'hall', 'rivera', 'campbell', 'mitchell',
    'carter', 'roberts', 'gomez', 'phillips', 'evans', 'turner', 'diaz',
    'parker', 'cruz', 'edwards', 'collins', 'reyes', 'stewart', 'morris',
    'morales', 'murphy', 'cook', 'rogers', 'gutierrez', 'ortiz', 'morgan',
    'cooper', 'peterson', 'bailey', 'reed', 'kelly', 'howard', 'ramos',
    'kim', 'cox', 'ward', 'richardson', 'watson', 'brooks', 'chavez',
    'wood', 'james', 'bennett', 'gray', 'mendoza', 'ruiz', 'hughes',
    'price', 'alvarez', 'castillo', 'sanders', 'patel', 'myers', 'long',
    'ross', 'foster', 'jimenez', 'powell', 'jenkins', 'perry', 'russell',
    'sullivan', 'bell', 'coleman', 'butler', 'henderson', 'barnes',
    'gonzalez', 'fisher', 'vasquez', 'simmons', 'patterson', 'jordan',
})


class YAKEKeywordExtractor:
    """
    YAKE! + spaCy NER keyword extractor.
    Drop-in replacement for the old LightweightKeywordExtractor.
    """

    # YAKE! scores are LOWER = more important (inverse of most systems)
    # We convert: relevance = 1 - normalised_yake_score  -> higher is better
    YAKE_SCORE_CAP = 0.5   # scores above this are noise
    MIN_KW_LEN     = 3
    ENTITY_TYPES   = {"PRODUCT", "EVENT",
                      "WORK_OF_ART", "LAW", "LANGUAGE"}

    # Entity types that should NOT be surfaced as study keywords.
    # PERSON is handled by _BLOCKED_NAMES; ORG/GPE are locations/orgs, not concepts.
    BLOCKED_ENTITY_TYPES = {"PERSON", "ORG", "GPE", "NORP", "FAC", "LOC"}

    # Multi-word candidates built around generic verbs / function words are
    # collocation fragments, not concepts ('converts sunlight', 'energy
    # stored', 'produce atp'). Single-word keywords are left alone -- the
    # plausibility gate downstream filters those.
    WEAK_PHRASE_TOKENS = frozenset({
        'converts', 'convert', 'converters', 'provide', 'provides', 'produced',
        'produce', 'produces', 'stored', 'store', 'stores', 'create', 'creates',
        'using', 'used', 'based', 'include', 'includes', 'including', 'following',
        'called', 'known', 'also', 'both', 'into', 'from', 'with', 'for',
        'during', 'after', 'before', 'the', 'and', 'a', 'an', 'of', 'to', 'in',
        'on', 'at', 'by', 'as', 'is', 'are', 'was', 'were', 'has', 'have',
        'studying', 'study', 'studies', 'learn', 'learning', 'about', 'will',
        'would', 'can', 'could', 'should', 'may', 'might', 'must', 'there',
        'their', 'this', 'that', 'these', 'those', 'over', 'under', 'which',
        'what', 'when', 'where', 'how', 'why', 'all', 'some', 'any', 'each',
        'not', 'very', 'more', 'most', 'other', 'such', 'than', 'then', 'than',
    })

    @staticmethod
    def _is_weak_phrase(keyword: str) -> bool:
        if ' ' not in keyword:
            return False
        return any(t in YAKEKeywordExtractor.WEAK_PHRASE_TOKENS for t in keyword.split())

    def extract_keywords(self, text: str, top_n: int = 15) -> List[Tuple[str, float]]:
        """
        Extract and rank keywords from a single text.

        Returns:
            List of (keyword, relevance_score) sorted high->low.
            relevance_score is in [0.0, 1.0].
        """
        if not text or len(text.strip()) < 10:
            return []

        scores: dict[str, float] = {}

        # -- 1. YAKE! extraction ------------------------------------
        yake = _get_yake()
        if yake is not None:
            try:
                raw = yake.extract_keywords(text)
                # raw = [(keyword, yake_score), ...]  lower score = more relevant
                if raw:
                    min_s = min(s for _, s in raw)
                    max_s = max(s for _, s in raw)
                    rng   = max(max_s - min_s, 1e-9)
                    for kw, s in raw:
                        kw = kw.lower().strip()
                        if len(kw) < self.MIN_KW_LEN:
                            continue
                        if s > self.YAKE_SCORE_CAP:
                            continue
                        # invert: low yake score -> high relevance
                        rel = 1.0 - (s - min_s) / rng
                        scores[kw] = max(scores.get(kw, 0.0), round(rel, 4))
            except Exception as e:
                logger.warning(f"YAKE! extraction failed: {e}")

        # -- 2. spaCy NER + noun chunks -----------------------------
        nlp = _get_nlp()
        blocked_entity_texts = set()
        if nlp is not None:
            try:
                doc = nlp(text[:50_000])  # cap for performance

                # Named entities -- skip blocked types, boost allowed types
                for ent in doc.ents:
                    if ent.label_ in self.BLOCKED_ENTITY_TYPES:
                        blocked_entity_texts.add(ent.text.lower().strip())
                        continue
                    if ent.label_ in self.ENTITY_TYPES:
                        kw = ent.text.lower().strip()
                        if len(kw) >= self.MIN_KW_LEN:
                            # entities get a floor score of 0.7
                            scores[kw] = max(scores.get(kw, 0.0), 0.7)

                # Noun chunks -- supplementary
                for chunk in doc.noun_chunks:
                    kw = chunk.root.lemma_.lower().strip()
                    if len(kw) >= self.MIN_KW_LEN and not chunk.root.is_stop:
                        scores[kw] = max(scores.get(kw, 0.0), 0.35)

                # Nouns and proper nouns not already captured
                for tok in doc:
                    if tok.pos_ in ("NOUN", "PROPN") and not tok.is_stop:
                        kw = tok.lemma_.lower().strip()
                        if len(kw) >= self.MIN_KW_LEN and kw.isalpha():
                            scores[kw] = max(scores.get(kw, 0.0), 0.25)
            except Exception as e:
                logger.warning(f"spaCy NER extraction failed: {e}")

        # -- 3. Fallback: word frequency if both pipelines failed ----
        if not scores:
            scores = self._frequency_fallback(text, top_n)

        # -- 4. Sort, cap, return ------------------------------------
        sorted_kws = sorted(scores.items(), key=lambda x: -x[1])
        # Drop weak verb/function-word phrase fragments (keep single words).
        sorted_kws = [kv for kv in sorted_kws if not self._is_weak_phrase(kv[0])]
        # Filter out keywords that are entirely personal names (PII)
        sorted_kws = [kv for kv in sorted_kws
                      if not all(w in _BLOCKED_NAMES for w in kv[0].split())]
        # Filter out keywords that are blocked entity text (ORG/GPE/etc.)
        if blocked_entity_texts:
            sorted_kws = [kv for kv in sorted_kws if kv[0] not in blocked_entity_texts]
        return sorted_kws[:top_n]

    @staticmethod
    def _frequency_fallback(text: str, top_n: int) -> dict:
        """Last-resort: normalised word frequency (no dependencies)."""
        from collections import Counter
        words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', text)]
        STOP  = {"the","and","for","with","that","this","are","was",
                 "were","have","has","from","they","their","you","your"}
        words = [w for w in words if w not in STOP]
        counts = Counter(words)
        total  = max(sum(counts.values()), 1)
        return {w: round(c/total, 4) for w, c in counts.most_common(top_n)}

    def get_keyword_scores_dict(self, text: str, top_n: int = 15) -> dict:
        """Return {keyword: score} dict for easy downstream use."""
        return {kw: sc for kw, sc in self.extract_keywords(text, top_n)}


# -- Global singleton -------------------------------------------------
_extractor_instance: Optional[YAKEKeywordExtractor] = None

def get_keyword_extractor() -> YAKEKeywordExtractor:
    """Return the global YAKE extractor instance (lazy init)."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = YAKEKeywordExtractor()
    return _extractor_instance


if __name__ == "__main__":
    text = (
        "Photosynthesis is the process by which plants convert sunlight into glucose "
        "using chlorophyll in the chloroplasts. The light-dependent reactions occur in "
        "the thylakoid membrane, while the Calvin cycle runs in the stroma. "
        "NASA has studied photosynthesis in microgravity environments."
    )
    extractor = YAKEKeywordExtractor()
    kws = extractor.extract_keywords(text, top_n=10)
    print("Top keywords:")
    for kw, sc in kws:
        bar = "█" * int(sc * 20)
        print(f"  {kw:<25} {sc:.4f}  {bar}")