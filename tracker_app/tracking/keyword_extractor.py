"""
Lightweight Keyword Extractor - KeyBERT Replacement

This module provides a lightweight alternative to KeyBERT using TF-IDF
and spaCy for keyword extraction, eliminating the 2GB+ PyTorch dependency.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
import spacy
import numpy as np
from typing import List, Tuple

class LightweightKeywordExtractor:
    """
    Lightweight keyword extractor using TF-IDF and spaCy.
    Drop-in replacement for KeyBERT with ~100x smaller footprint.
    """
    
    def __init__(self, model_name='en_core_web_sm'):
        """Initialize with spaCy model"""
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"spaCy model '{model_name}' not found. Run: python -m spacy download {model_name}")
            self.nlp = None
        
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=1
        )
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Extract keywords from text using TF-IDF.
        
        Args:
            text: Input text
            top_n: Number of keywords to extract
            
        Returns:
            List of (keyword, score) tuples
        """
        if not text or not text.strip():
            return []
        
        # Use spaCy for better tokenization if available
        if self.nlp:
            doc = self.nlp(text)
            # Filter out stop words, punctuation, and short tokens
            tokens = [
                token.text.lower() 
                for token in doc 
                if not token.is_stop 
                and not token.is_punct 
                and len(token.text) > 2
                and token.is_alpha
            ]
            
            # Also extract noun phrases
            noun_phrases = [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text) > 3]
            
            # Combine tokens and noun phrases
            processed_text = ' '.join(tokens + noun_phrases)
        else:
            processed_text = text.lower()
        
        if not processed_text.strip():
            return []
        
        try:
            # Fit TF-IDF on the processed text
            tfidf_matrix = self.vectorizer.fit_transform([processed_text])
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Get scores
            scores = tfidf_matrix.toarray()[0]
            
            # Sort by score
            top_indices = np.argsort(scores)[::-1][:top_n]
            
            keywords = [
                (feature_names[idx], float(scores[idx]))
                for idx in top_indices
                if scores[idx] > 0
            ]
            
            return keywords
            
        except Exception as e:
            print(f"Keyword extraction error: {e}")
            return []
    
    def extract_keywords_batch(self, texts: List[str], top_n: int = 5) -> List[List[Tuple[str, float]]]:
        """Extract keywords from multiple texts"""
        return [self.extract_keywords(text, top_n) for text in texts]


# Global instance (lazy loaded)
_extractor_instance = None

def get_keyword_extractor():
    """Get or create global keyword extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = LightweightKeywordExtractor()
    return _extractor_instance
