import datetime

class SessionManager:
    def __init__(self):
        self.reset_session()

    def reset_session(self):
        """Initialize or reset the session object."""
        self.session_data = {
            'timestamp': datetime.datetime.now(),
            'app': None,
            'window_title': None,
            'interaction_rate': None,
            'ocr_text': None,
            'keywords': [],
            'embedding': None,
            'audio_label': None,
            'audio_confidence': None,
            'attention_score': None,   # optional, used if camera consent = True
            'intent_label': None,
            'intent_confidence': None,
            'memory_score': None,
            'next_review_time': None
        }

    def update(self, key, value):
        """Update a single field in the session object."""
        if key in self.session_data:
            self.session_data[key] = value
        else:
            raise KeyError(f"{key} is not a valid session field")

    def get(self):
        """Return the current session data."""
        return self.session_data
