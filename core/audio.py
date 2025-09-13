import pyaudio
import wave
import threading
import time
import os
from datetime import datetime
import logging
import json
from pathlib import Path

# Import the Whisper transcriber
from .audio_whisper import whisper_transcriber

logger = logging.getLogger(__name__)

class AudioMonitor:
    def __init__(self, output_dir="data/audio", sample_rate=16000, chunk_size=1024):
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_recording = False
        self.audio_thread = None
        self.db_manager = None
        self.audio_processor = None
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Audio monitor initialized. Output directory: {output_dir}")
        
    def start_recording(self, duration=10):
        """Record audio for specified duration"""
        def record_audio():
            try:
                audio = pyaudio.PyAudio()
                
                # Check if microphone is available
                if audio.get_device_count() == 0:
                    logger.error("No audio devices found")
                    return None
                
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
                
                logger.info(f"🎤 Recording audio for {duration} seconds...")
                frames = []
                
                for _ in range(0, int(self.sample_rate / self.chunk_size * duration)):
                    if not self.is_recording:
                        break
                    data = stream.read(self.chunk_size)
                    frames.append(data)
                
                stream.stop_stream()
                stream.close()
                audio.terminate()
                
                if not frames:
                    return None
                
                # Save audio file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(self.output_dir, f"audio_{timestamp}.wav")
                
                wf = wave.open(filename, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                logger.info(f"💾 Audio saved: {filename}")
                return filename
                
            except Exception as e:
                logger.error(f"Audio recording error: {e}")
                return None
        
        return record_audio()
    
    def start_continuous_monitoring(self, interval=300, db_manager=None, audio_processor=None):
        """Start continuous audio monitoring with database integration"""
        self.is_recording = True
        self.db_manager = db_manager
        self.audio_processor = audio_processor
        
        def monitoring_loop():
            while self.is_recording:
                try:
                    audio_file = self.start_recording(duration=30)  # Record 30-second clips
                    if audio_file and self.db_manager and self.audio_processor:
                        # Process and save to database
                        transcription = self.audio_processor.transcribe_audio(audio_file)
                        
                        if transcription['success']:
                            # Analyze content
                            analysis = self.audio_processor.analyze_audio_content(transcription['text'])
                            
                            # Save to database
                            self.db_manager.save_audio_recording(
                                file_path=audio_file,
                                timestamp=datetime.now().isoformat(),
                                duration=30,
                                transcribed_text=transcription['text'],
                                confidence=transcription['confidence'],
                                word_count=transcription['word_count'],
                                keywords=analysis['keywords'],
                                is_educational=analysis['is_educational']
                            )
                            logger.info(f"💾 Audio saved to database: {audio_file}")
                        else:
                            logger.warning(f"❌ Transcription failed for: {audio_file}")
                    
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Audio monitoring error: {e}")
                    time.sleep(10)  # Wait before retrying
        
        self.audio_thread = threading.Thread(target=monitoring_loop)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        logger.info("🎤 Audio monitoring started with database integration")
    
    def stop_monitoring(self):
        """Stop audio monitoring"""
        self.is_recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=5.0)
        logger.info("🎤 Audio monitoring stopped")

class AudioProcessor:
    def __init__(self):
        self.supported_formats = ['.wav', '.mp3', '.flac']
        logger.info("Audio processor initialized")
    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio file using Whisper
        """
        try:
            # Convert to absolute path and ensure file exists
            audio_path = str(Path(audio_path).absolute())
            
            # Wait for file to be fully written (more robust check)
            max_attempts = 5
            for attempt in range(max_attempts):
                if Path(audio_path).exists() and Path(audio_path).stat().st_size > 0:
                    break
                time.sleep(0.5)
            else:
                logger.error(f"Audio file never appeared: {audio_path}")
                return self._fallback_transcription()
            
            logger.info(f"🔊 Transcribing audio: {Path(audio_path).name}")
            
            # Use Whisper for actual transcription
            result = whisper_transcriber.transcribe_audio(audio_path)
            
            if result['success'] and result['text'].strip():
                logger.info(f"✅ Transcription successful: {result['word_count']} words")
                return {
                    'text': result['text'],
                    'confidence': 0.9,
                    'word_count': result['word_count'],
                    'success': True,
                    'language': result.get('language', 'en')
                }
            else:
                logger.warning("❌ Transcription failed or empty, using fallback")
                return self._fallback_transcription()
                
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return self._fallback_transcription()
    def _fallback_transcription(self):
        """Fallback if Whisper fails"""
        return {
            'text': 'Audio transcription failed. Please check audio quality.',
            'confidence': 0.0,
            'word_count': 0,
            'success': False
        }
    
    def analyze_audio_content(self, transcribed_text):
        """
        Analyze transcribed audio content for knowledge extraction
        """
        if not transcribed_text or not transcribed_text.strip():
            return {
                'keywords': [],
                'keyword_count': 0,
                'is_educational': False
            }
        
        # Enhanced keyword list for better knowledge detection
        knowledge_keywords = [
            'learn', 'study', 'read', 'watch', 'understand', 'concept', 'theory',
            'practice', 'exam', 'test', 'quiz', 'homework', 'research', 'article',
            'paper', 'book', 'chapter', 'section', 'tutorial', 'course', 'lesson',
            'lecture', 'explain', 'teach', 'educate', 'knowledge', 'skill', 'training',
            'workshop', 'webinar', 'seminar', 'presentation', 'documentation', 'guide',
            'manual', 'textbook', 'reference', 'material', 'curriculum', 'syllabus',
            'assignment', 'project', 'thesis', 'dissertation', 'research', 'analysis',
            'calculate', 'solve', 'problem', 'equation', 'formula', 'code', 'program',
            'develop', 'build', 'create', 'design', 'architecture', 'algorithm', 'data',
            'statistics', 'math', 'physics', 'chemistry', 'biology', 'history', 'science',
            'technology', 'engineering', 'medicine', 'law', 'business', 'economics',
            'finance', 'psychology', 'philosophy', 'literature', 'language', 'culture'
        ]
        
        text_lower = transcribed_text.lower()
        found_keywords = []
        
        for keyword in knowledge_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        # More sophisticated educational content detection
        word_count = len(transcribed_text.split())
        keyword_density = len(found_keywords) / max(word_count, 1)
        
        # Consider it educational if we have at least 2 keywords or high density
        is_educational = (len(found_keywords) >= 2 or 
                         (word_count > 20 and keyword_density > 0.1))
        
        return {
            'keywords': found_keywords,
            'keyword_count': len(found_keywords),
            'keyword_density': keyword_density,
            'is_educational': is_educational,
            'word_count': word_count
        }