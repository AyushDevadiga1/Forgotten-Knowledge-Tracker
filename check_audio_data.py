#!/usr/bin/env python3
import os
from core.database import DatabaseManager
from core.audio import AudioProcessor

def check_audio_data():
    print("🔍 Checking Audio Database Functionality")
    print("==================================================")
    
    # Use a real database file
    db = DatabaseManager("test_audio.db")
    audio_processor = AudioProcessor()

    # Test the database save functionality
    test_text = "I need to learn this concept for my exam tomorrow"
    analysis = audio_processor.analyze_audio_content(test_text)

    print("1. Testing database save...")
    # Save to database
    success = db.save_audio_recording(
        file_path="/test/path/audio_test.wav",
        timestamp="2023-12-07T10:30:00",
        duration=30,
        transcribed_text=test_text,
        confidence=0.95,
        word_count=len(test_text.split()),
        keywords=analysis['keywords'],
        is_educational=analysis['is_educational']
    )

    print(f"   ✅ Save successful: {success}")

    print("2. Testing data retrieval...")
    # Check if data was saved
    recordings = db.get_audio_recordings()
    print(f"   ✅ Recordings in database: {len(recordings)}")
    
    for recording in recordings:
        print(f"      - File: {recording['file_path']}")
        print(f"        Words: {recording['word_count']}")
        print(f"        Keywords: {recording['keywords']}")
        print(f"        Educational: {recording['is_educational']}")

    print("3. Testing audio statistics...")
    stats = db.get_audio_stats()
    print(f"   ✅ Total recordings: {stats.get('total_recordings', 0)}")
    print(f"   ✅ Total duration: {stats.get('total_duration_seconds', 0)}s")
    print(f"   ✅ Educational content: {stats.get('educational_content_count', 0)}")

    # Clean up
    if os.path.exists("test_audio.db"):
        os.remove("test_audio.db")
    
    print("==================================================")
    print("🎉 Audio database functionality verified!")

if __name__ == "__main__":
    check_audio_data()