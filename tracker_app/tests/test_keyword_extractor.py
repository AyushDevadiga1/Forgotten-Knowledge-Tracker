"""Tests: YAKE keyword extractor singleton config (M-10).

Per-call language/max_ngram/top_n parameters on `_get_yake()` used to be
silently ignored after the first init because YAKE bakes its configuration
into the instance at construction. The parameters are now gone and the
singleton's fixed config (en / bigram / top 20) is documented.

Run: python -m pytest tracker_app/tests/test_keyword_extractor.py -v
"""

import inspect

from tracker_app.tracking import keyword_extractor as kw


def test_get_yake_accepts_no_parameters():
    assert list(inspect.signature(kw._get_yake).parameters) == []


def test_get_yake_singleton_has_fixed_config():
    extractor = kw._get_yake()
    if extractor is None:
        return  # YAKE! not installed - nothing to assert

    assert kw._get_yake() is extractor  # singleton reused
    assert extractor.config["lan"] == "en"
    assert extractor.config["n"] == 2
    assert extractor.config["top"] == 20
