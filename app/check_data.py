#!/usr/bin/env python3
import os
import sqlite3

# Path to your database
db_path = 'data/tracking.db'

if not os.path.exists(db_path):
    print("❌ Database file doesn't exist!")
    print("Please run your tracker first to create the database")
    exit()

# Check what tables exist
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("📊 Database tables:", [table[0] for table in tables])

# Check data counts
for table in ['window_history', 'screenshots', 'audio_recordings']:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"📈 {table}: {count} records")

conn.close()