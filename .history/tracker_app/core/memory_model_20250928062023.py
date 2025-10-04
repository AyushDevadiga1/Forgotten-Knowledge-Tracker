import numpy as np
from datetime import datetime, timedelta
from config import MEMORY_THRESHOLD
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)

# NEW: Novel Memory Network Implementation
class MultiModalMemoryNetwork(nn.Module):
    """
    IEEE Novel: Multi-scale memory network with cross-modal attention
    """
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=1):
        super().__init__()
        self.hidden_dim = hidden_dim
        
        # Cross-modal fusion
        self.fusion_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # Temporal memory LSTM
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True, num_layers=2)
        
        # Multi-scale attention
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4)
        
        # Ebbinghaus-inspired decay
        self.decay_predictor = nn.Sequential(
            nn.Linear(hidden_dim + 1, hidden_dim // 2),  # +1 for time
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Sigmoid()
        )
        
    def forward(self, features, time_deltas):
        # Feature fusion
        fused = self.fusion_layer(features)
        
        # Temporal modeling
        lstm_out, _ = self.lstm(fused.unsqueeze(1))
        
        # Attention mechanism
        attended, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Combine with time information
        time_expanded = time_deltas.unsqueeze(-1)
        combined = torch.cat([attended.squeeze(1), time_expanded], dim=1)
        
        # Memory score prediction
        memory_score = self.decay_predictor(combined)
        return memory_score

# Initialize the novel model (CPU for compatibility)
try:
    novel_memory_model = MultiModalMemoryNetwork()
    # Load pre-trained weights if available
    try:
        novel_memory_model.load_state_dict(torch.load('models/memory_model.pth', map_location='cpu'))
        logger.info("Loaded pre-trained memory model")
    except:
        logger.info("Using untrained novel memory model")
    novel_memory_model.eval()
except Exception as e:
    logger.error(f"Failed to initialize novel memory model: {e}")
    novel_memory_model = None

# ORIGINAL FUNCTIONS - PRESERVED
def compute_memory_score(last_review_time, lambda_val, intent_conf=1.0, attention_score=50, audio_conf=1.0):
    """
    ORIGINAL: Compute memory score using Ebbinghaus forgetting curve
    """
    if isinstance(last_review_time, str):
        last_review_time = datetime.fromisoformat(last_review_time)
    
    t = (datetime.now() - last_review_time).total_seconds() / 3600  # time in hours
    R_t = np.exp(-lambda_val * t)  # basic Ebbinghaus curve

    # Normalize attention_score (0-100) to 0-1
    att_factor = attention_score / 100

    # Weighted memory
    memory_score = R_t * intent_conf * att_factor * audio_conf
    return memory_score

def schedule_next_review(last_review_time, memory_score, lambda_val, hours_min=1):
    """
    ORIGINAL: Compute next review time based on memory score
    """
    if isinstance(last_review_time, str):
        last_review_time = datetime.fromisoformat(last_review_time)
    
    if memory_score < MEMORY_THRESHOLD:
        # Simple adaptive logic: sooner if memory is low
        next_review = datetime.now() + timedelta(hours=hours_min)
    else:
        # Longer interval if memory is high
        next_review = last_review_time + timedelta(hours=1/lambda_val)
    return next_review

# NEW: Enhanced memory scoring with novel network
def compute_memory_score_enhanced(concept_data, ocr_confidence=0.5, audio_confidence=0.5, 
                                 attention_score=50, interaction_rate=0, app_type="unknown"):
    """
    Enhanced memory scoring using novel multi-modal network
    """
    # Fallback to original if novel model not available
    if novel_memory_model is None:
        last_review = concept_data.get('last_review_time', datetime.now())
        return compute_memory_score(last_review, 0.1, 1.0, attention_score, 1.0)
    
    try:
        # Prepare features for novel model
        features = torch.tensor([
            ocr_confidence,
            audio_confidence, 
            attention_score / 100.0,
            min(interaction_rate / 10.0, 1.0),
            # App type encoding
            1.0 if app_type in ["study", "browser", "document"] else 0.0,
            concept_data.get('count', 1) / 10.0  # Normalized concept frequency
        ], dtype=torch.float32).unsqueeze(0)
        
        # Time since last review (hours)
        last_review = concept_data.get('last_review_time', datetime.now())
        if isinstance(last_review, str):
            last_review = datetime.fromisoformat(last_review)
        time_delta = torch.tensor([(datetime.now() - last_review).total_seconds() / 3600], 
                                dtype=torch.float32).unsqueeze(0)
        
        # Predict with novel model
        with torch.no_grad():
            memory_score = novel_memory_model(features, time_delta).item()
        
        # Enhanced scheduling
        next_review = schedule_next_review_enhanced(last_review, memory_score, concept_data)
        
        return {
            'memory_score': memory_score,
            'next_review': next_review,
            'method': 'novel_network',
            'features_used': features.shape[1]
        }
        
    except Exception as e:
        logger.error(f"Enhanced memory scoring failed: {e}")
        # Fallback to original method
        last_review = concept_data.get('last_review_time', datetime.now())
        memory_score = compute_memory_score(last_review, 0.1, 1.0, attention_score, 1.0)
        return {
            'memory_score': memory_score,
            'next_review': schedule_next_review(last_review, memory_score, 0.1),
            'method': 'fallback_original'
        }

def schedule_next_review_enhanced(last_review, memory_score, concept_data):
    """
    Enhanced scheduling using adaptive intervals
    """
    base_interval = 1  # hours
    
    # Adaptive interval based on memory score and concept frequency
    concept_freq = concept_data.get('count', 1)
    adaptive_factor = max(0.5, min(2.0, (1.0 - memory_score) * concept_freq))
    
    interval_hours = base_interval * adaptive_factor
    
    # Ensure reasonable bounds
    interval_hours = max(0.1, min(24, interval_hours))
    
    return datetime.now() + timedelta(hours=interval_hours)

# NEW: Adaptive threshold based on context
def get_adaptive_memory_threshold(concept_count, average_confidence, time_of_day=None):
    """
    Adjust memory threshold based on context
    """
    base_threshold = MEMORY_THRESHOLD
    
    # Adjust based on concept count
    count_factor = min(concept_count / 50.0, 0.3)  # Max 30% adjustment
    
    # Adjust based on confidence
    confidence_factor = (average_confidence - 0.5) * 0.2
    
    # Time-of-day adjustment
    time_factor = 0.0
    if time_of_day is None:
        time_of_day = datetime.now().hour
    
    if 9 <= time_of_day <= 17:  # Working hours - more sensitive
        time_factor = -0.1
    elif 22 <= time_of_day or time_of_day <= 6:  # Sleep hours - less sensitive
        time_factor = 0.1
    
    adaptive_threshold = base_threshold + count_factor + confidence_factor + time_factor
    
    return max(0.3, min(0.9, adaptive_threshold))

# Example usage
if __name__ == "__main__":
    # Test both systems
    concept_data = {
        'last_review_time': datetime.now() - timedelta(hours=5),
        'count': 3
    }
    
    print("Original memory score:", 
          compute_memory_score(concept_data['last_review_time'], 0.1, 0.8, 75, 1.0))
    
    enhanced_result = compute_memory_score_enhanced(
        concept_data, 0.8, 0.7, 85, 5, "browser"
    )
    print("Enhanced memory score:", enhanced_result)