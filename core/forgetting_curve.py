import math
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ForgettingCurve:
    def __init__(self):
        """Initialize with Ebbinghaus forgetting curve parameters"""
        # Ebbinghaus intervals (days) for optimal spaced repetition
        self.intervals = [0.04, 1, 2, 5, 8, 14, 30]  # 1 hour, 1 day, 2 days, etc.
        self.retention_threshold = 0.3  # Schedule review when retention drops below 30%
        
    def calculate_retention(self, last_seen_date: datetime, memory_strength: float = 1.0) -> float:
        """
        Calculate current retention percentage using Ebbinghaus exponential decay formula
        R = e^(-t/S) where t is time passed and S is memory strength
        """
        if not isinstance(last_seen_date, datetime):
            try:
                last_seen_date = datetime.fromisoformat(last_seen_date.replace('Z', '+00:00'))
            except:
                logger.error(f"Invalid date format: {last_seen_date}")
                return 0.0
        
        time_passed = (datetime.now() - last_seen_date).total_seconds() / 86400  # Convert to days
        retention = math.exp(-time_passed / (memory_strength * 10))
        return max(0.0, min(1.0, retention))  # Clamp between 0-1
    
    def calculate_memory_strength(self, knowledge_item: Dict) -> float:
        """
        Calculate memory strength based on various factors
        Higher strength = slower forgetting
        """
        strength = 1.0  # Base strength
        
        # Boost strength for educational content
        if knowledge_item.get('is_educational', False):
            strength *= 1.5
        
        # Boost strength for longer engagement
        if 'duration' in knowledge_item and knowledge_item['duration'] > 60:
            strength *= 1.2
        
        # Boost strength for high word count (more content)
        if 'word_count' in knowledge_item and knowledge_item['word_count'] > 50:
            strength *= 1.3
        
        # Boost strength for multiple keywords
        if 'keywords' in knowledge_item and len(knowledge_item['keywords']) > 3:
            strength *= 1.4
            
        return min(strength, 3.0)  # Cap maximum strength
    
    def get_next_review_time(self, knowledge_item: Dict) -> Optional[datetime]:
        """
        Calculate optimal review time based on memory strength and forgetting curve
        Returns None if no review needed yet
        """
        try:
            timestamp = knowledge_item.get('timestamp')
            if not timestamp:
                return None
            
            # Convert to datetime if it's a string
            if isinstance(timestamp, str):
                last_seen = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                last_seen = timestamp
            
            # Calculate memory strength and current retention
            memory_strength = self.calculate_memory_strength(knowledge_item)
            current_retention = self.calculate_retention(last_seen, memory_strength)
            
            logger.debug(f"Retention for '{knowledge_item.get('title', 'unknown')}': {current_retention:.2%}")
            
            # If retention below threshold, schedule review
            if current_retention < self.retention_threshold:
                # Use appropriate interval based on how long it's been
                hours_passed = (datetime.now() - last_seen).total_seconds() / 3600
                
                if hours_passed < 1:
                    interval_index = 0  # 1 hour
                elif hours_passed < 24:
                    interval_index = 1  # 1 day
                elif hours_passed < 48:
                    interval_index = 2  # 2 days
                else:
                    # Find the appropriate interval
                    days_passed = hours_passed / 24
                    for i, interval in enumerate(self.intervals):
                        if days_passed < interval:
                            interval_index = i
                            break
                    else:
                        interval_index = len(self.intervals) - 1  # Use last interval
                
                review_in_days = self.intervals[interval_index]
                return last_seen + timedelta(days=review_in_days)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating review time: {e}")
            return None
    
    def get_review_suggestions(self, knowledge_items: List[Dict], limit: int = 10) -> List[Dict]:
        """
        Get suggestions for what to review based on forgetting curve
        """
        suggestions = []
        
        for item in knowledge_items:
            review_time = self.get_next_review_time(item)
            if review_time:
                retention = self.calculate_retention(
                    item.get('timestamp'), 
                    self.calculate_memory_strength(item)
                )
                
                suggestions.append({
                    'item': item,
                    'review_time': review_time,
                    'urgency': 1 - retention,  # Higher urgency = more urgent
                    'retention_score': retention
                })
        
        # Sort by urgency (most urgent first)
        suggestions.sort(key=lambda x: x['urgency'], reverse=True)
        return suggestions[:limit]

# Global instance
forgetting_curve = ForgettingCurve()