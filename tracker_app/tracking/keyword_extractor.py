"""
FKT 2.0 — Keyword Extractor (YAKE! + spaCy NER)
=================================================
Replaces the broken TF-IDF single-document extractor with YAKE!
(Yet Another Keyword Extractor) — a statistical, corpus-free algorithm
that actually ranks keywords by importance within a single document.

Why YAKE! beats TF-IDF here:
  TF-IDF on ONE document gives every term the same score (= 1.0).
  YAKE! uses term frequency, casing, position, co-occurrence, and
  sentence dispersion within the single text — real ranking without
  needing a background corpus.

Pipeline:
  1. YAKE!          → ranked keyword candidates (statistical)
  2. spaCy NER      → named entities (PERSON, ORG, GPE, PRODUCT, EVENT)
  3. spaCy nouns    → noun chunks as supplementary candidates
  4. Merge + dedup  → final scored keyword dict

Fallback: if YAKE! is not installed, falls back to spaCy noun extraction.
"""

import logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger("KeywordExtractor")

# ── Lazy-loaded heavy objects ────────────────────────────────
_yake_extractor = None
_spacy_nlp      = None

def _get_yake(language="en", max_ngram=2, top_n=20):
    """Return a YAKE extractor instance (lazy init)."""
    global _yake_extractor
    if _yake_extractor is None:
        try:
            import yake
            _yake_extractor = yake.KeywordExtractor(
                lan=language,
                n=max_ngram,
                dedupLim=0.7,      # deduplicate near-identical keywords
                dedupFunc="seqm",
                windowsSize=2,
                top=top_n,
                features=None,
            )
            logger.info("YAKE! keyword extractor initialised.")
        except ImportError:
            logger.warning("YAKE! not installed. Run: pip install yake")
            _yake_extractor = None
    return _yake_extractor

def _get_nlp():
    """Return spaCy nlp model (lazy init)."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            _spacy_nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm loaded for keyword extraction.")
        except Exception as e:
            logger.warning(f"spaCy load failed: {e}")
            _spacy_nlp = None
    return _spacy_nlp


class YAKEKeywordExtractor:
    """
    YAKE! + spaCy NER keyword extractor.
    Drop-in replacement for the old LightweightKeywordExtractor.
    """

    # YAKE! scores are LOWER = more important (inverse of most systems)
    # We convert: relevance = 1 - normalised_yake_score  → higher is better
    YAKE_SCORE_CAP = 0.5   # scores above this are noise
    MIN_KW_LEN     = 3
    ENTITY_TYPES   = {"PERSON", "ORG", "GPE", "PRODUCT", "EVENT",
                      "WORK_OF_ART", "LAW", "LANGUAGE"}

    def extract_keywords(self, text: str, top_n: int = 15) -> List[Tuple[str, float]]:
        """
        Extract and rank keywords from a single text.

        Returns:
            List of (keyword, relevance_score) sorted high→low.
            relevance_score is in [0.0, 1.0].
        """
        if not text or len(text.strip()) < 10:
            return []

        scores: dict[str, float] = {}

        # ── 1. YAKE! extraction ──────────────────────────────
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
                        # invert: low yake score → high relevance
                        rel = 1.0 - (s - min_s) / rng
                        scores[kw] = max(scores.get(kw, 0.0), round(rel, 4))
            except Exception as e:
                logger.warning(f"YAKE! extraction failed: {e}")

        # ── 2. spaCy NER + noun chunks ───────────────────────
        nlp = _get_nlp()
        if nlp is not None:
            try:
                doc = nlp(text[:50_000])  # cap for performance

                # Named entities — highest-value signal
                for ent in doc.ents:
                    if ent.label_ in self.ENTITY_TYPES:
                        kw = ent.text.lower().strip()
                        if len(kw) >= self.MIN_KW_LEN:
                            # entities get a floor score of 0.7
                            scores[kw] = max(scores.get(kw, 0.0), 0.7)

                # Noun chunks — supplementary
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

        # ── 3. Fallback: word frequency if both pipelines failed ─
        if not scores:
            scores = self._frequency_fallback(text, top_n)

        # ── 4. Sort, cap, return ─────────────────────────────
        sorted_kws = sorted(scores.items(), key=lambda x: -x[1])
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

    def extract_keywords_batch(self, texts: List[str], top_n: int = 15
                               ) -> List[List[Tuple[str, float]]]:
        return [self.extract_keywords(t, top_n) for t in texts]

    def get_keyword_scores_dict(self, text: str, top_n: int = 15) -> dict:
        """Return {keyword: score} dict for easy downstream use."""
        return {kw: sc for kw, sc in self.extract_keywords(text, top_n)}


# ── Global singleton ────────────────────────────────────────
_extractor_instance: Optional[YAKEKeywordExtractor] = None

def get_keyword_extractor() -> YAKEKeywordExtractor:
    """Return the global YAKE extractor instance (lazy init)."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = YAKEKeywordExtractor()
    return _extractor_instance

# Legacy alias so nothing breaks
LightweightKeywordExtractor = YAKEKeywordExtractor


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
