import whisper
import logging
import torch
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Whisper will use device: {self.device}")
        
    def load_model(self):
        """Load Whisper model (lazy loading)"""
        if self.model is None:
            logger.info(f"Loading Whisper model ({self.model_size})...")
            start_time = time.time()
            self.model = whisper.load_model(self.model_size, device=self.device)
            load_time = time.time() - start_time
            logger.info(f"Whisper model loaded in {load_time:.2f} seconds")
        return self.model
    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio file using OpenAI Whisper
        Returns: {'text': str, 'word_count': int, 'success': bool}
        """
        try:
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            model = self.load_model()
            
            # Transcribe audio
            logger.info(f"Transcribing: {audio_path}")
            start_time = time.time()
            result = model.transcribe(audio_path)
            transcription_time = time.time() - start_time
            
            text = result['text'].strip()
            word_count = len(text.split())
            
            logger.info(f"Transcription completed in {transcription_time:.2f}s: {word_count} words")
            
            return {
                'text': text,
                'word_count': word_count,
                'success': True,
                'language': result.get('language', 'en'),
                'processing_time': transcription_time
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {
                'text': '',
                'word_count': 0,
                'success': False,
                'error': str(e)
            }

# Global instance
whisper_transcriber = WhisperTranscriber(model_size="base")