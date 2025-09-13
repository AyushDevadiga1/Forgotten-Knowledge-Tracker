#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.audio_whisper import WhisperTranscriber
from core.audio import AudioProcessor

def test_whisper():
    print("🎵 Testing Whisper Integration")
    print("==================================================")
    
    # Test with a sample audio file if you have one, or it will use fallback
    transcriber = WhisperTranscriber()
    processor = AudioProcessor()
    
    # Test transcription
    print("1. Testing Whisper model loading...")
    transcriber.load_model()
    print("   ✅ Model loaded successfully")
    
    # Test with a non-existent file to test fallback
    print("2. Testing fallback mechanism...")
    result = processor.transcribe_audio("non_existent.wav")
    print(f"   ✅ Fallback test: {result['success']}")
    print(f"   Text: {result['text'][:50]}...")
    
    print("3. Testing content analysis...")
    test_text = "I need to study for my physics exam and learn about quantum mechanics"
    analysis = processor.analyze_audio_content(test_text)
    print(f"   ✅ Keywords: {analysis['keywords']}")
    print(f"   Educational: {analysis['is_educational']}")
    
    print("==================================================")
    print("🎉 Whisper integration ready!")
    print("Next: Run your tracker to capture real audio for transcription")

if __name__ == "__main__":
    test_whisper()