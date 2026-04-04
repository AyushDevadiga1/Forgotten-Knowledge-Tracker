"""
Cognitive Load Estimator (CLe) — FKT 2.0 Novel Feature
========================================================
Estimates real-time cognitive load from keystroke dynamics WITHOUT requiring
a webcam. Used as the primary attention signal when webcam is disabled, and
as a complementary signal when webcam IS enabled.

Research basis:
  - Epp et al. (2011): Identifying emotional states using keystroke dynamics
  - Vizer et al. (2009): Automated stress detection using keystroke and linguistic features
  - Monrose & Rubin (2000): Keystroke dynamics as a biometric

Signals used:
  1. Inter-key interval (IKI) entropy     → high entropy = high cognitive engagement
  2. Typing speed variance                → irregular speed = high load
  3. Backspace rate                       → editing = higher cognitive effort
  4. Pause density                        → frequent pauses = processing/thinking
  5. Burst length distribution            → short bursts = shallow processing

Output: cle_score 0.0–1.0
  0.0–0.3  = Idle / passive browsing
  0.3–0.6  = Light cognitive load (reading, media)
  0.6–0.8  = Moderate load (active reading, note-taking)
  0.8–1.0  = High load (coding, problem-solving, writing)
"""

import time
import math
import logging
from collections import deque
from threading import Lock
from typing import Optional

logger = logging.getLogger("CLe")

# ----------------------------
# Constants
# ----------------------------
WINDOW_SECONDS = 30          # Rolling window for CLE calculation
MIN_EVENTS_FOR_SCORE = 5     # Minimum events before issuing a score
PAUSE_THRESHOLD_MS = 1500    # Gap longer than this = a "pause" (ms)
BURST_GAP_MS = 300           # Gap shorter than this = same typing burst


class CognitiveLoadEstimator:
    """
    Thread-safe, lightweight cognitive load estimator using keystroke dynamics.
    Works completely offline with zero ML model dependencies.
    """

    def __init__(self, window_seconds: int = WINDOW_SECONDS):
        self._lock = Lock()
        self._window_seconds = window_seconds

        # Circular buffer: (timestamp_ms, event_type)
        # event_type: 'key' | 'backspace' | 'mouse'
        self._events: deque = deque()

        # Running stats
        self._total_keys = 0
        self._total_backspaces = 0
        self._session_start = time.time()

    def record_key(self, is_backspace: bool = False):
        """Record a keypress event (call from pynput on_press)."""
        now_ms = time.time() * 1000
        with self._lock:
            event_type = 'backspace' if is_backspace else 'key'
            self._events.append((now_ms, event_type))
            if is_backspace:
                self._total_backspaces += 1
            else:
                self._total_keys += 1
            self._prune_old_events(now_ms)

    def record_mouse_click(self):
        """Record a mouse click (lighter signal than keypress)."""
        now_ms = time.time() * 1000
        with self._lock:
            self._events.append((now_ms, 'mouse'))
            self._prune_old_events(now_ms)

    def _prune_old_events(self, now_ms: float):
        """Remove events outside the rolling window (call with lock held)."""
        cutoff = now_ms - (self._window_seconds * 1000)
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def get_cle_score(self) -> dict:
        """
        Compute the current cognitive load estimate.

        Returns:
            {
                'cle_score': float,          # 0.0–1.0
                'label': str,                # 'idle'|'passive'|'light'|'moderate'|'high'
                'confidence': float,         # 0.0–1.0 (low if too few events)
                'signals': dict,             # breakdown of individual signals
                'event_count': int
            }
        """
        now_ms = time.time() * 1000

        with self._lock:
            self._prune_old_events(now_ms)
            events = list(self._events)

        if len(events) < MIN_EVENTS_FOR_SCORE:
            return {
                'cle_score': 0.0,
                'label': 'idle',
                'confidence': 0.0,
                'signals': {},
                'event_count': len(events)
            }

        key_events = [(ts, t) for ts, t in events if t in ('key', 'backspace')]
        backspace_events = [ts for ts, t in events if t == 'backspace']

        if len(key_events) < 2:
            return {
                'cle_score': 0.1,
                'label': 'passive',
                'confidence': 0.2,
                'signals': {},
                'event_count': len(events)
            }

        timestamps = [ts for ts, _ in key_events]

        # --- Signal 1: Inter-key interval entropy ---
        ikis = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        ikis_filtered = [iki for iki in ikis if 0 < iki < 5000]  # discard absurd gaps

        iki_entropy = 0.0
        if ikis_filtered:
            # Bucket IKIs into bins and compute Shannon entropy
            buckets = [0] * 10
            for iki in ikis_filtered:
                bucket = min(int(iki / 200), 9)  # 200ms buckets
                buckets[bucket] += 1
            total = sum(buckets)
            probs = [b / total for b in buckets if b > 0]
            iki_entropy = -sum(p * math.log2(p) for p in probs)
            iki_entropy_norm = min(iki_entropy / 3.32, 1.0)  # max entropy for 10 buckets ≈ 3.32
        else:
            iki_entropy_norm = 0.0

        # --- Signal 2: Typing speed variance ---
        if len(ikis_filtered) > 1:
            mean_iki = sum(ikis_filtered) / len(ikis_filtered)
            variance = sum((x - mean_iki) ** 2 for x in ikis_filtered) / len(ikis_filtered)
            cv = (variance ** 0.5) / mean_iki if mean_iki > 0 else 0  # coefficient of variation
            speed_variance_norm = min(cv / 2.0, 1.0)
        else:
            speed_variance_norm = 0.0

        # --- Signal 3: Backspace rate ---
        backspace_rate = len(backspace_events) / max(len(key_events), 1)
        backspace_norm = min(backspace_rate / 0.25, 1.0)  # 25% backspace rate = max score

        # --- Signal 4: Pause density ---
        all_gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        pauses = [g for g in all_gaps if g > PAUSE_THRESHOLD_MS]
        pause_density = len(pauses) / max(len(all_gaps), 1)
        # Moderate pauses = thinking = higher load; too many pauses = idle
        pause_score = 1.0 - abs(pause_density - 0.3) / 0.3 if pause_density <= 0.6 else 0.0
        pause_score = max(0.0, pause_score)

        # --- Signal 5: Burst analysis ---
        # Bursts = sequences of rapid keypresses separated by longer gaps
        bursts = []
        current_burst = 1
        for gap in all_gaps:
            if gap < BURST_GAP_MS:
                current_burst += 1
            else:
                bursts.append(current_burst)
                current_burst = 1
        bursts.append(current_burst)

        avg_burst_length = sum(bursts) / len(bursts) if bursts else 1
        burst_score = min(avg_burst_length / 15.0, 1.0)  # long bursts = sustained engagement

        # --- Combine signals with weights ---
        # Weights determined empirically from keystroke dynamics literature
        signals = {
            'iki_entropy': round(iki_entropy_norm, 3),
            'speed_variance': round(speed_variance_norm, 3),
            'backspace_rate': round(backspace_norm, 3),
            'pause_score': round(pause_score, 3),
            'burst_score': round(burst_score, 3),
        }

        weights = {
            'iki_entropy': 0.30,
            'speed_variance': 0.20,
            'backspace_rate': 0.20,
            'pause_score': 0.15,
            'burst_score': 0.15,
        }

        cle_score = sum(signals[k] * weights[k] for k in signals)
        cle_score = max(0.0, min(cle_score, 1.0))

        # Confidence based on number of events
        confidence = min(len(key_events) / 30.0, 1.0)

        # Label
        if cle_score < 0.15:
            label = 'idle'
        elif cle_score < 0.35:
            label = 'passive'
        elif cle_score < 0.55:
            label = 'light'
        elif cle_score < 0.75:
            label = 'moderate'
        else:
            label = 'high'

        return {
            'cle_score': round(cle_score, 3),
            'label': label,
            'confidence': round(confidence, 3),
            'signals': signals,
            'event_count': len(events)
        }

    def get_session_stats(self) -> dict:
        """Get overall session keystroke stats."""
        elapsed = time.time() - self._session_start
        return {
            'total_keys': self._total_keys,
            'total_backspaces': self._total_backspaces,
            'backspace_rate': self._total_backspaces / max(self._total_keys, 1),
            'elapsed_minutes': round(elapsed / 60, 1),
            'keys_per_minute': round(self._total_keys / max(elapsed / 60, 0.01), 1),
        }

    def reset(self):
        """Reset the estimator for a new session."""
        with self._lock:
            self._events.clear()
            self._total_keys = 0
            self._total_backspaces = 0
            self._session_start = time.time()


# ----------------------------
# Global instance (shared with loop.py)
# ----------------------------
_cle_instance: Optional[CognitiveLoadEstimator] = None

def get_cle() -> CognitiveLoadEstimator:
    """Get or create the global CLE instance."""
    global _cle_instance
    if _cle_instance is None:
        _cle_instance = CognitiveLoadEstimator()
    return _cle_instance


if __name__ == "__main__":
    import random
    cle = CognitiveLoadEstimator(window_seconds=30)

    print("Simulating 60 keypresses with realistic timing...")
    base = time.time()
    for i in range(60):
        is_bs = random.random() < 0.08  # 8% backspace rate
        cle.record_key(is_backspace=is_bs)
        time.sleep(random.uniform(0.05, 0.4))

    result = cle.get_cle_score()
    print(f"\nCLE Score: {result['cle_score']:.3f} ({result['label']})")
    print(f"Confidence: {result['confidence']:.2f}")
    print("Signals:")
    for k, v in result['signals'].items():
        print(f"  {k}: {v:.3f}")
    print(f"\nSession stats: {cle.get_session_stats()}")
