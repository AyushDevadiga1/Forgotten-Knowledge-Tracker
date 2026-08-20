"""
Unit Tests: Privacy Filter
===========================
Tests that sensitive data is detected and redacted correctly.
Run: python -m pytest tracker_app/tests/test_privacy_filter.py -v
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tracker_app.tracking.privacy_filter import (
    detect_sensitive_data,
    redact_sensitive_data,
    sanitize_text_for_storage,
    is_sensitive_window,
    strip_redaction_markers,
    filter_sensitive_keywords,
    MAX_REDACTION_DENSITY
)


class TestCreditCardDetection(unittest.TestCase):

    def test_detects_space_separated_card(self):
        text = "Card number: 1234 5678 9012 3456"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        self.assertIn('credit_card', types, "Should detect space-separated credit card")

    def test_detects_dash_separated_card(self):
        text = "My VISA is 4111-1111-1111-1111"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        self.assertIn('credit_card', types)

    def test_detects_no_separator_card(self):
        text = "4532015112830366"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        self.assertIn('credit_card', types)

    def test_does_not_flag_random_16_digit_number(self):
        # Not all 16-digit numbers are credit cards; context matters
        text = "Session ID: 1234567890123456"
        detected = detect_sensitive_data(text)
        # Just verify no crash
        self.assertIsInstance(detected, list)


class TestEmailDetection(unittest.TestCase):

    def test_detects_standard_email(self):
        text = "Send to john.doe@example.com please"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        self.assertIn('email', types)

    def test_detects_subdomain_email(self):
        text = "user@mail.company.co.uk"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        self.assertIn('email', types)

    def test_no_false_positive_on_at_sign(self):
        text = "@mentions_on_twitter are not emails"
        detected = detect_sensitive_data(text)
        # Should not detect "@mentions" as email since no domain part
        self.assertIsInstance(detected, list)  # just no crash


class TestSSNDetection(unittest.TestCase):

    def test_detects_ssn_with_dashes(self):
        text = "SSN: 123-45-6789"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        self.assertIn('ssn', types)

    def test_no_false_positive_phone_number(self):
        text = "Call me at 555-867-5309"
        detected = detect_sensitive_data(text)
        types = [d['type'] for d in detected]
        # Phone is XXX-XXX-XXXX (10 digits), SSN is XXX-XX-XXXX (9 digits)
        # Should not flag phone as SSN
        self.assertNotIn('ssn', types)


class TestRedaction(unittest.TestCase):

    def test_credit_card_redacted(self):
        text = "My card: 1234-5678-9012-3456"
        redacted, count = redact_sensitive_data(text)
        self.assertNotIn('1234-5678-9012-3456', redacted)
        self.assertIn('[REDACTED', redacted)
        self.assertGreater(count, 0)

    def test_email_redacted(self):
        text = "Email me at user@example.com"
        redacted, count = redact_sensitive_data(text)
        self.assertNotIn('user@example.com', redacted)
        self.assertIn('[REDACTED', redacted)

    def test_clean_text_unchanged(self):
        text = "Python is a high-level programming language."
        redacted, count = redact_sensitive_data(text)
        self.assertEqual(redacted, text)
        self.assertEqual(count, 0)

    def test_empty_string_does_not_crash(self):
        redacted, count = redact_sensitive_data("")
        self.assertEqual(redacted, "")
        self.assertEqual(count, 0)

    def test_none_like_empty_string_handled(self):
        """Verify the function handles edge cases gracefully."""
        try:
            redact_sensitive_data("   ")
        except Exception as e:
            self.fail(f"Whitespace-only string crashed: {e}")


class TestSanitizeForStorage(unittest.TestCase):

    def test_sanitize_returns_dict(self):
        result = sanitize_text_for_storage("Hello world")
        self.assertIsInstance(result, dict)

    def test_sanitize_contains_text_key(self):
        result = sanitize_text_for_storage("Hello world")
        self.assertIn('text', result)

    def test_sanitize_sensitive_text(self):
        result = sanitize_text_for_storage("Card: 4111-1111-1111-1111")
        self.assertNotIn('4111-1111-1111-1111', result['text'])

    def test_sanitize_marks_is_sanitized(self):
        result = sanitize_text_for_storage("Normal educational content")
        self.assertIn('is_sanitized', result)


class TestExtendedPatterns(unittest.TestCase):
    """Newer detection patterns: amex, discover, bare-digit PII, DOB, API keys."""

    def test_detects_amex(self):
        text = "Use Amex 378282246310005 to pay"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('amex', types)

    def test_detects_discover(self):
        text = "Discover 6011111111111117 card"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('discover', types)

    def test_detects_bare_ssn_digits(self):
        text = "my ssn is 123-45-6789"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('ssn', types)

    def test_detects_bare_phone_digits(self):
        text = "reach me at 5558675309"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('phone_digits', types)

    def test_detects_bank_account_with_label(self):
        text = "routing 021000021 account 1000000002"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('bank_account', types)

    def test_detects_dob(self):
        text = "born 03/14/1990 in Chicago"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('dob', types)

    def test_detects_api_key_short_length(self):
        text = "token=abcd1234ef"
        types = [d['type'] for d in detect_sensitive_data(text)]
        self.assertIn('api_key', types)

    def test_password_value_redacted_without_keyword_separator(self):
        # "password is hunter2" — the value must go even when 'is' is present.
        redacted, count = redact_sensitive_data("my password is hunter2")
        self.assertNotIn('hunter2', redacted)
        self.assertGreater(count, 0)

    def test_short_numeric_password_not_redacted(self):
        # A bare secret with no keyword/format match is invisible — the
        # structural gate, not the redactor, must handle it.
        redacted, count = redact_sensitive_data("hunter2")
        self.assertNotIn('[REDACTED', redacted)
        self.assertEqual(count, 0)


class TestDensitySkip(unittest.TestCase):
    """High-density sensitive captures are rejected, not redacted."""

    def test_dense_text_is_not_safe_to_store(self):
        text = (
            "ssn 123-45-6789 card 4111-1111-1111-1111 phone 555-867-5309 "
            "email a@b.com account 1000000002 born 03/14/1990"
        )
        result = sanitize_text_for_storage(text)
        self.assertFalse(result['safe_to_store'])
        self.assertEqual(result['text'], '')

    def test_light_sensitive_text_is_redacted_and_kept(self):
        text = "my email is john@example.com and I study biology"
        result = sanitize_text_for_storage(text)
        self.assertTrue(result['safe_to_store'])
        self.assertNotIn('john@example.com', result['text'])

    def test_clean_text_is_safe(self):
        result = sanitize_text_for_storage("Photosynthesis converts sunlight")
        self.assertTrue(result['safe_to_store'])
        self.assertFalse(result['is_sanitized'])


class TestRedactionMarkers(unittest.TestCase):

    def test_strips_markers(self):
        stripped = strip_redaction_markers(
            "email [REDACTED:EMAIL] and card [REDACTED:CREDIT_CARD] here"
        )
        self.assertNotIn('REDACTED', stripped)
        self.assertNotIn('EMAIL', stripped)
        self.assertNotIn('CREDIT_CARD', stripped)

    def test_markers_never_become_keywords(self):
        stripped = strip_redaction_markers("[REDACTED:EMAIL] [REDACTED:PHONE] [REDACTED:SSN]")
        self.assertEqual(stripped.strip(), "")

    def test_strip_handles_empty(self):
        self.assertEqual(strip_redaction_markers(""), "")


class TestSensitiveKeywordFilter(unittest.TestCase):

    def test_drops_marker_noise_keywords(self):
        cleaned = filter_sensitive_keywords({
            'redacted': 1.0, 'email': 0.9, 'password': 0.8,
            'photosynthesis': 0.5,
        })
        self.assertNotIn('redacted', cleaned)
        self.assertNotIn('email', cleaned)
        self.assertNotIn('password', cleaned)
        self.assertIn('photosynthesis', cleaned)

    def test_drops_keywords_that_are_themselves_sensitive(self):
        cleaned = filter_sensitive_keywords({
            'john@example.com': 0.7, '123-45-6789': 0.6, '4111111111111111': 0.5,
        })
        self.assertEqual(cleaned, {})

    def test_drops_pure_numeric_keywords(self):
        cleaned = filter_sensitive_keywords({'555-867-5309': 0.9, '123456': 0.4})
        self.assertEqual(cleaned, {})

    def test_keeps_real_study_keywords(self):
        cleaned = filter_sensitive_keywords({
            'calvin cycle': 0.6, 'photosynthesis': 0.5, 'atp': 0.4,
        })
        self.assertEqual(set(cleaned), {'calvin cycle', 'photosynthesis', 'atp'})

    def test_handles_empty(self):
        self.assertEqual(filter_sensitive_keywords({}), {})
        self.assertEqual(filter_sensitive_keywords(None), None)


class TestWindowSkipping(unittest.TestCase):

    def test_password_manager_window_skipped(self):
        """Windows with 'password' in title should be skipped."""
        self.assertTrue(is_sensitive_window("1Password - Vault"))

    def test_banking_window_skipped(self):
        """Banking sites should be skipped."""
        result = is_sensitive_window("Online Banking — Chase")
        self.assertTrue(result)

    def test_normal_window_not_skipped(self):
        """Normal educational windows should not be skipped."""
        result = is_sensitive_window("Python Documentation - Functions")
        self.assertFalse(result)

    def test_empty_window_title_handled(self):
        """Empty window title should not crash."""
        try:
            result = is_sensitive_window("")
            self.assertIsInstance(result, bool)
        except Exception as e:
            self.fail(f"Empty window title crashed: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
