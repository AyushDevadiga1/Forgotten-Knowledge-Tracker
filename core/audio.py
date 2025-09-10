import pyaudio
import wave
import threading
import time
import os
from datetime import datetime
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioMonitor:
    def __init__(self, output_dir="data/audio", sample_rate=16000, chunk_size=1024):
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_recording = False
        self.audio_thread = None
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
                
                logger.info(f"Recording audio for {duration} seconds...")
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
                
                logger.info(f"Audio saved: {filename}")
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
                    
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Audio monitoring error: {e}")
                    time.sleep(10)  # Wait before retrying
        
        self.audio_thread = threading.Thread(target=monitoring_loop)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        logger.info("🎤 Audio monitoring started")
    
    def stop_monitoring(self):
        """Stop audio monitoring"""
        self.is_recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=5.0)
        logger.info("Audio monitoring stopped")

class AudioProcessor:
    def __init__(self):
        self.supported_formats = ['.wav', '.mp3', '.flac']
        logger.info("Audio processor initialized")
    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio file to text using speech recognition
        Note: This is a placeholder - you'll need to implement actual speech recognition
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")
            
            # For now, return placeholder text
            # You can integrate with:
            # - OpenAI Whisper
            # - Google Speech-to-Text
            # - Mozilla DeepSpeech
            # - Microsoft Azure Speech
            
            return {
                'text': 'Audio transcription placeholder. Implement speech-to-text service.',
                'confidence': 0.0,
                'word_count': 5,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'word_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def analyze_audio_content(self, transcribed_text):
        """
        Analyze transcribed audio content for knowledge extraction
        """
        # Simple keyword-based analysis
        knowledge_keywords = [
            'learn', 'study', 'read', 'watch', 'understand', 'concept',
            'theory', 'practice', 'exam', 'test', 'quiz', 'homework',
            'research', 'article', 'paper', 'book', 'chapter', 'section'
        ]
        
        found_keywords = []
        for keyword in knowledge_keywords:
            if keyword.lower() in transcribed_text.lower():
                found_keywords.append(keyword)
        
        return {
            'keywords': found_keywords,
            'keyword_count': len(found_keywords),
            'is_educational': len(found_keywords) > 2
        }