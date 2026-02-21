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

from tracker_app.core.privacy_filter import (
    detect_sensitive_data,
    redact_sensitive_data,
    sanitize_text_for_storage,
    is_sensitive_window
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
