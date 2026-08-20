"""Forgotten Knowledge Tracker (FKT) package"""
__version__ = "2.0.0"


def check_spacy_model():
    """Verify spaCy model is installed. Log warning if missing."""
    import logging
    logger = logging.getLogger("FKT")
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' not found. "
            "Install with: python -m spacy download en_core_web_sm"
        )
