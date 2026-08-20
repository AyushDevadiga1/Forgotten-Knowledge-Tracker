"""
Tests: Concept Filtering Gaps (TDD — must FAIL before fixes)
=============================================================

Three bugs in the concept-filtering pipeline that let non-concept noise
through:

  Bug 1: PERSON/ORG/GPE entities are extracted as keywords.
         spaCy NER names/places/companies are not study concepts and can be PII.

  Bug 2: Trigram coverage at 30% lets gibberish through.
         Words like "abtion" pass because "tion" alone gives 67% coverage.

  Bug 3: filter_sensitive_keywords does not catch common personal names.

Run: python -m pytest tracker_app/tests/test_concept_filtering_gaps.py -v
"""

import pytest

from tracker_app.tracking.keyword_extractor import YAKEKeywordExtractor
from tracker_app.learning.text_quality_validator import is_plausible_concept
from tracker_app.tracking.privacy_filter import filter_sensitive_keywords


# ── Bug 1: PERSON / ORG / GPE extracted as keywords ────────────


class TestKeywordExtractorExcludesEntityTypes:
    """The keyword extractor should NOT surface PERSON, ORG, or GPE
    named entities as study-concept keywords — they are PII and noise."""

    def test_keyword_extractor_excludes_person_entities(self):
        """'John Smith' is a PERSON entity and must not appear as a keyword."""
        extractor = YAKEKeywordExtractor()
        text = "John Smith studied biology at the university for his degree."
        keywords = extractor.get_keyword_scores_dict(text)
        keyword_names = set(keywords.keys())

        assert "john smith" not in keyword_names, (
            "PERSON entity 'john smith' should not be a keyword — it is PII, "
            f"but was found in: {keyword_names}"
        )

    def test_keyword_extractor_excludes_org_entities(self):
        """'Stanford University' is an ORG entity and must not appear."""
        extractor = YAKEKeywordExtractor()
        text = "Stanford University published new research on photosynthesis."
        keywords = extractor.get_keyword_scores_dict(text)
        keyword_names = set(keywords.keys())

        assert "stanford university" not in keyword_names, (
            "ORG entity 'stanford university' should not be a keyword — "
            f"but was found in: {keyword_names}"
        )

    def test_keyword_extractor_excludes_gpe_entities(self):
        """'Mountain View' is a GPE entity and must not appear."""
        extractor = YAKEKeywordExtractor()
        text = "Mountain View is where many technology companies are based."
        keywords = extractor.get_keyword_scores_dict(text)
        keyword_names = set(keywords.keys())

        assert "mountain view" not in keyword_names, (
            "GPE entity 'mountain view' should not be a keyword — "
            f"but was found in: {keyword_names}"
        )


# ── Bug 2: Trigram coverage gate at 30% ─────────────────────────


class TestPlausibleConceptRejectsGibberish:
    """Gibberish words that happen to contain common trigrams (like 'tion')
    should still be rejected — the 30% trigram threshold is too permissive."""

    def test_plausible_concept_rejects_gibberish_with_trigram_overlap(self):
        """'abtion' is not a word but has 'tion' = 4/6 chars = 67% coverage,
        which exceeds the 30% gate and lets it through."""
        assert is_plausible_concept("abtion") is False, (
            "'abtion' is gibberish and should be rejected, but passed the "
            "trigram coverage gate (has 'tion' → 67% coverage)"
        )

    def test_plausible_concept_rejects_other_trigram_gibberish(self):
        """'netion' has 'tion' = 4/6 = 67% but is not a real word."""
        assert is_plausible_concept("netion") is False, (
            "'netion' is gibberish and should be rejected"
        )


# ── Bug 3: filter_sensitive_keywords misses common names ────────


class TestFilterSensitiveKeywordsRemovesNames:
    """filter_sensitive_keywords should remove common personal names
    that could be PII, but currently only checks SENSITIVE_KEYWORD_NOISE
    and PII regex patterns."""

    def test_filter_sensitive_keywords_removes_common_names(self):
        """'john' and 'smith' are common personal names and should be removed."""
        keywords = {"john": 0.9, "smith": 0.8, "biology": 0.5}
        cleaned = filter_sensitive_keywords(keywords)

        assert "john" not in cleaned, (
            "Personal name 'john' should be filtered out as PII"
        )
        assert "smith" not in cleaned, (
            "Personal name 'smith' should be filtered out as PII"
        )
        assert "biology" in cleaned, (
            "Non-PII keyword 'biology' should be kept"
        )
