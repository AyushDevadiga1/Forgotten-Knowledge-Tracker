from datetime import datetime, timedelta
import numpy as np
from config import SM2_INITIAL_EASE, SM2_MINIMUM_EASE

class SM2Scheduler:
    """
    Implementation of SM-2 spaced repetition algorithm
    Based on: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
    """
    
    def __init__(self, initial_ease=SM2_INITIAL_EASE, min_ease=SM2_MINIMUM_EASE):
        self.initial_ease = initial_ease
        self.min_ease = min_ease
    
    def calculate_next_review(self, quality, previous_interval=None, previous_ease=None, previous_reps=None):
        """
        SM-2 algorithm implementation
        
        Parameters:
        quality: 0-5 rating (0=complete blackout, 5=perfect response)
        previous_interval: previous interval in days (None for first review)
        previous_ease: previous ease factor (None for first review)
        previous_reps: number of previous repetitions (None for first review)
        
        Returns:
        Dictionary with scheduling information
        """
        if previous_interval is None:
            previous_interval = 1
        if previous_ease is None:
            previous_ease = self.initial_ease
        if previous_reps is None:
            previous_reps = 0
        
        if quality >= 3:  # Correct response (quality 3,4,5)
            if previous_reps == 0:
                interval = 1
            elif previous_reps == 1:
                interval = 6
            else:
                interval = previous_interval * previous_ease
                
            repetitions = previous_reps + 1
            ease_factor = previous_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            ease_factor = max(self.min_ease, ease_factor)  # Minimum ease factor
        else:  # Incorrect response (quality 0,1,2) - reset
            interval = 1
            repetitions = 0
            ease_factor = previous_ease  # Keep the same ease factor
        
        next_review = datetime.now() + timedelta(days=int(round(interval)))
        
        return {
            'interval': interval,
            'ease_factor': ease_factor,
            'repetitions': repetitions,
            'next_review': next_review,
            'quality': quality
        }
    
    def map_confidence_to_quality(self, ocr_confidence, audio_confidence, attention_score, interaction_rate, app_type):
        """
        Map multi-modal signals to SM-2 quality rating (0-5)
        
        Parameters:
        ocr_confidence: Confidence in OCR text extraction (0-1)
        audio_confidence: Confidence in audio classification (0-1)
        attention_score: Webcam attention score (0-100)
        interaction_rate: Keyboard/mouse interaction rate
        app_type: Type of application (browser, document, entertainment, etc.)
        
        Returns:
        Quality rating 0-5 for SM-2 algorithm
        """
        # Base confidence from OCR and audio
        base_confidence = (ocr_confidence * 0.4 + audio_confidence * 0.3)
        
        # Attention factor (normalized 0-1)
        attention_factor = attention_score / 100.0 if attention_score else 0.5
        
        # Interaction factor (capped at 1.0)
        interaction_factor = min(interaction_rate / 10.0, 1.0)
        
        # App type multiplier
        app_multiplier = 1.0
        if app_type in ["browser", "document", "study"]:
            app_multiplier = 1.2  # Boost for study apps
        elif app_type == "entertainment":
            app_multiplier = 0.6  # Penalty for entertainment apps
        
        # Combined quality score (0-5 scale)
        quality_score = (base_confidence * 0.4 + 
                        attention_factor * 0.3 + 
                        interaction_factor * 0.3) * app_multiplier * 5
        
        # Ensure quality is between 0 and 5
        quality = max(0, min(5, quality_score))
        
        return quality
    
    def get_concept_memory_score(self, concept_data):
        """
        Calculate current memory score for a concept based on SM-2 state
        """
        if not concept_data:
            return 0.3  # Default low score for new concepts
        
        last_review = concept_data.get('last_review_time', datetime.now())
        if isinstance(last_review, str):
            last_review = datetime.fromisoformat(last_review)
        
        interval = concept_data.get('interval', 1)
        ease_factor = concept_data.get('ease_factor', self.initial_ease)
        repetitions = concept_data.get('repetitions', 0)
        
        # Calculate days since last review
        days_since_review = (datetime.now() - last_review).days
        
        if repetitions == 0:  # New concept
            memory_score = max(0.1, 1.0 - (days_since_review / 7.0))
        else:
            # Memory decays based on interval and time passed
            optimal_interval = interval * ease_factor
            memory_score = max(0.1, 1.0 - (days_since_review / optimal_interval))
        
        return memory_score

# Singleton instance for global use
sm2_scheduler = SM2Scheduler()

# Example usage
if __name__ == "__main__":
    scheduler = SM2Scheduler()
    
    # Test first review (quality 4)
    result1 = scheduler.calculate_next_review(quality=4)
    print("First review (quality 4):", result1)
    
    # Test subsequent review (quality 5)
    result2 = scheduler.calculate_next_review(
        quality=5, 
        previous_interval=result1['interval'],
        previous_ease=result1['ease_factor'],
        previous_reps=result1['repetitions']
    )
    print("Second review (quality 5):", result2)
    
    # Test quality mapping
    quality = scheduler.map_confidence_to_quality(
        ocr_confidence=0.8,
        audio_confidence=0.9,
        attention_score=85,
        interaction_rate=12,
        app_type="browser"
    )
    print(f"Mapped quality score: {quality:.2f}")