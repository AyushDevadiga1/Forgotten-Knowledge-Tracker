"""Tests for selective entity filtering in keyword extraction.

Verifies that:
- PERSON names are blocked from becoming keywords
- ORG entities (companies, institutions) ARE allowed
- GPE entities (countries, cities) ARE allowed
"""
import pytest
from tracker_app.tracking.keyword_extractor import YAKEKeywordExtractor, get_keyword_extractor


@pytest.fixture
def extractor():
    return get_keyword_extractor()


class TestEntityFiltering:
    def test_person_names_blocked(self, extractor):
        """PERSON entities should not appear as keywords."""
        text = "John Smith works at Stanford University in California"
        kws = extractor.get_keyword_scores_dict(text)
        kw_names = set(kws.keys())
        # Person names should be blocked
        assert "john" not in kw_names
        assert "smith" not in kw_names
        # But the organization should pass through
        assert "stanford" in kw_names or "stanford university" in kw_names

    def test_organization_allowed(self, extractor):
        """ORG entities should be extractable as keywords."""
        text = "Google published a paper on transformer architecture"
        kws = extractor.get_keyword_scores_dict(text)
        kw_names = set(kws.keys())
        # Organization should be allowed
        assert "google" in kw_names

    def test_location_allowed(self, extractor):
        """GPE entities should be extractable as keywords."""
        text = "The French Revolution began in Paris, France"
        kws = extractor.get_keyword_scores_dict(text)
        kw_names = set(kws.keys())
        # Locations should be allowed
        assert "france" in kw_names or "paris" in kw_names

    def test_blocked_entity_types_only_person(self):
        """BLOCKED_ENTITY_TYPES should only contain PERSON."""
        assert YAKEKeywordExtractor.BLOCKED_ENTITY_TYPES == {"PERSON"}


class TestPOSBigramFiltering:
    def test_verb_noun_bigram_rejected(self, extractor):
        """Bigrams containing verbs should be rejected."""
        text = "John Smith works at Microsoft developing machine learning algorithms"
        kws = extractor.get_keyword_scores_dict(text)
        kw_names = set(kws.keys())
        # These verb+ noun bigrams should NOT appear
        assert "smith works" not in kw_names
        assert "microsoft developing" not in kw_names
        assert "developing machine" not in kw_names

    def test_noun_noun_bigram_kept(self, extractor):
        """Noun+noun bigrams should be kept."""
        text = "The neural network architecture uses transformer attention mechanism"
        kws = extractor.get_keyword_scores_dict(text)
        kw_names = set(kws.keys())
        # These noun+noun bigrams SHOULD appear
        assert "neural network" in kw_names
        assert "attention mechanism" in kw_names
        assert "network architecture" in kw_names

    def test_single_words_not_affected(self, extractor):
        """Single-word keywords should not be affected by POS filtering."""
        text = "Photosynthesis is the process by which plants convert light energy"
        kws = extractor.get_keyword_scores_dict(text)
        kw_names = set(kws.keys())
        # Single words should still appear
        assert "photosynthesis" in kw_names or "process" in kw_names
