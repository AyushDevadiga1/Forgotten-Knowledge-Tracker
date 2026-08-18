"""
Sensitive Data Filter

Detects and redacts sensitive information from OCR text.
"""

import re
from typing import Tuple, List

# Sensitive data patterns (raw strings)
SENSITIVE_PATTERNS_RAW = {
    'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    'amex':        r'\b3[47]\d{13}\b',
    'discover':    r'\b6(?:011|5\d{2})\d{12}\b',
    'ssn':         r'\b\d{3}-\d{2}-\d{4}\b',
    'ssn_digits':  r'\b(?!000|666|9\d{2})\d{3}(?!00)\d{2}(?!0000)\d{4}\b',
    'email':       r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'phone':       r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
    'phone_digits': r'(?:^|(?<=\s))(?:\+?1[-.]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}(?:\s|$)',
    'bank_account': r'\b(?:acct|account|routing|iban|a\/c|sort\s?code)\b\s*#?\s*\d[\d\- ]{3,17}',
    'dob':          r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    'password_field': r'\b(?:password|passcode|passwd|pwd)\b\s*(?:is|was|has been|becomes)?\s*[:=]?\s*\S+',
    'api_key': r'\b(?:api[_-]?key|token|bearer|auth[_-]?token|access[_-]?key|secret[_-]?key)\b[:=\s]+\S{10,}',
    'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
}

# Keywords that only exist because a redaction marker (or a sensitive value)
# reached the extractor â€” never legitimate study concepts on their own.
# (Defense-in-depth: the markers are stripped before extraction, so this list
# only catches stragglers.)
SENSITIVE_KEYWORD_NOISE = frozenset({
    'redacted', 'email', 'phone', 'ssn', 'card', 'credit', 'password',
    'passcode', 'passwd', 'pwd', 'field', 'token', 'bearer', 'acct',
    'routing', 'iban',
})

# Sensitive density at which the whole capture is skipped rather than redacted.
MAX_REDACTION_DENSITY = 3

# Pre-compile patterns for performance
SENSITIVE_PATTERNS = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in SENSITIVE_PATTERNS_RAW.items()
}

# Privacy-sensitive window titles
SENSITIVE_WINDOW_KEYWORDS = [
    'password', 'login', 'sign in', 'authentication',
    'bank', 'paypal', 'credit card', 'payment',
    'private', 'incognito', 'inprivate',
    'medical', 'health', 'prescription'
]

def detect_sensitive_data(text: str) -> List[dict]:
    """
    Detect sensitive data in text using pre-compiled patterns.
    
    Returns list of detected patterns with type and position.
    """
    detections = []
    
    for pattern_name, compiled_pattern in SENSITIVE_PATTERNS.items():
        matches = compiled_pattern.finditer(text)
        for match in matches:
            detections.append({
                'type': pattern_name,
                'value': match.group(),
                'start': match.start(),
                'end': match.end()
            })
    
    return detections

def redact_sensitive_data(text: str) -> Tuple[str, int]:
    """
    Redact sensitive data from text using pre-compiled patterns.
    
    Returns:
        (redacted_text, num_redactions)
    """
    redacted_text = text
    num_redactions = 0
    
    for pattern_name, compiled_pattern in SENSITIVE_PATTERNS.items():
        matches = list(compiled_pattern.finditer(redacted_text))
        for match in reversed(matches):  # Reverse to maintain indices
            # Replace with [REDACTED: type]
            replacement = f'[REDACTED:{pattern_name.upper()}]'
            redacted_text = (
                redacted_text[:match.start()] + 
                replacement + 
                redacted_text[match.end():]
            )
            num_redactions += 1
    
    return redacted_text, num_redactions

def is_sensitive_window(window_title: str) -> bool:
    """Check if window title suggests sensitive content"""
    if not window_title:
        return False
    
    title_lower = window_title.lower()
    return any(keyword in title_lower for keyword in SENSITIVE_WINDOW_KEYWORDS)

def should_skip_capture(window_title: str, text: str = None) -> Tuple[bool, str]:
    """
    Determine if capture should be skipped for privacy.
    
    Returns:
        (should_skip, reason)
    """
    # Check window title
    if is_sensitive_window(window_title):
        return True, f"Sensitive window: {window_title}"
    
    # Check text content if provided
    if text:
        detections = detect_sensitive_data(text)
        if len(detections) > 3:  # More than 3 sensitive items
            return True, f"High sensitive data density ({len(detections)} items)"
    
    return False, None

def sanitize_text_for_storage(text: str) -> dict:
    """
    Sanitize text before storage.

    Sensitive values are redacted in place. If the text is dense with
    sensitive data (more than MAX_REDACTION_DENSITY hits), the whole capture
    is rejected (safe_to_store=False) â€” redacting one value out of a page of
    PII still leaves the rest as usable concepts, which defeats the point.

    Returns dict with sanitized text and metadata.
    """
    if not text:
        return {
            'text': text,
            'is_sanitized': False,
            'num_redactions': 0,
            'detected_types': [],
            'safe_to_store': True,
        }

    detections = detect_sensitive_data(text)

    # High-density sensitive content â†’ reject the whole capture.
    if len(detections) > MAX_REDACTION_DENSITY:
        return {
            'text': '',
            'is_sanitized': True,
            'num_redactions': len(detections),
            'detected_types': sorted(set(d['type'] for d in detections)),
            'safe_to_store': False,
        }

    # Redact if needed
    if detections:
        redacted_text, num_redactions = redact_sensitive_data(text)
        return {
            'text': redacted_text,
            'is_sanitized': True,
            'num_redactions': num_redactions,
            'detected_types': sorted(set(d['type'] for d in detections)),
            'safe_to_store': True
        }

    return {
        'text': text,
        'is_sanitized': False,
        'num_redactions': 0,
        'detected_types': [],
        'safe_to_store': True
    }


_REDACTION_MARKER_RE = re.compile(r'\[REDACTED:[A-Z_]+\]')


def strip_redaction_markers(text: str) -> str:
    """Remove [REDACTED:TYPE] markers so they never become keywords.

    The markers are informative for humans but must not reach keyword
    extraction â€” 'email', 'phone', 'password' etc. are not study concepts.
    """
    if not text:
        return text
    return _REDACTION_MARKER_RE.sub('', text)


def filter_sensitive_keywords(keywords) -> dict:
    """
    Drop extracted keywords that are themselves sensitive data or redaction
    marker noise. Input: {keyword: score} dict. Output: cleaned dict.
    """
    if not keywords:
        return keywords

    clean = {}
    for kw, score in keywords.items():
        if not kw:
            continue
        k = str(kw).strip().lower()
        if not k:
            continue
        if k in SENSITIVE_KEYWORD_NOISE:
            continue
        if detect_sensitive_data(k):
            continue
        if '@' in k:
            continue
        # Pure numeric / phone-like / decimal junk is never a concept.
        if k.isdigit() or re.fullmatch(r'[\d\s.\-()]+', k):
            continue
        clean[kw] = score
    return clean
