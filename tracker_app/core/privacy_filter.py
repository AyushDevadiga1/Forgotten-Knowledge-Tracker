"""
Sensitive Data Filter

Detects and redacts sensitive information from OCR text.
"""

import re
from typing import Tuple, List

# Sensitive data patterns (raw strings)
SENSITIVE_PATTERNS_RAW = {
    'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
    'password_field': r'password[:=\s]+\S+',
    'api_key': r'(api[_-]?key|token)[:=\s]+[A-Za-z0-9_\-]{20,}',
    'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
}

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

def redact_sensitive_data(text: str, redaction_char: str = '*') -> Tuple[str, int]:
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
    
    Returns dict with sanitized text and metadata.
    """
    # Detect sensitive data
    detections = detect_sensitive_data(text)
    
    # Redact if needed
    if detections:
        redacted_text, num_redactions = redact_sensitive_data(text)
        return {
            'text': redacted_text,
            'is_sanitized': True,
            'num_redactions': num_redactions,
            'detected_types': list(set(d['type'] for d in detections)),
            'safe_to_store': True
        }
    
    return {
        'text': text,
        'is_sanitized': False,
        'num_redactions': 0,
        'detected_types': [],
        'safe_to_store': True
    }
