#!/usr/bin/env python3
import os
from core.database import DatabaseManager
from core.audio import AudioProcessor

# Use a real database file instead of :memory:
db = DatabaseManager("test_audio.db")
audio_processor = AudioProcessor()

# Test the database save functionality
test_text = "I need to learn this concept for my exam tomorrow"
analysis = audio_processor.analyze_audio_content(test_text)

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

print(f"Save successful: {success}")

# Check if data was saved
recordings = db.get_audio_recordings()
print(f"Recordings in database: {len(recordings)}")
for recording in recordings:
    print(f"  - {recording['file_path']}: {recording['word_count']} words")

# Clean up
if os.path.exists("test_audio.db"):
    os.remove("test_audio.db")