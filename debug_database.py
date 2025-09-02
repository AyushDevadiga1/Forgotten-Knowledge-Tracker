#!/usr/bin/env python3
"""
Database diagnostic tool to identify the save screenshot issue
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    print("Testing Database Connection...")
    print("=" * 50)
    
    try:
        from core.database import DatabaseManager
        
        # Initialize database
        db = DatabaseManager("data/tracking.db")
        print("✅ Database manager initialized")
        
        # Check if database file exists
        if os.path.exists("data/tracking.db"):
            print("✅ Database file exists")
            file_size = os.path.getsize("data/tracking.db")
            print(f"   File size: {file_size} bytes")
        else:
            print("❌ Database file does not exist")
            return False
        
        # Test basic query
        total_screenshots = db.get_screenshot_count()
        total_ocr = db.get_ocr_result_count()
        print(f"✅ Current screenshot count: {total_screenshots}")
        print(f"✅ Current OCR result count: {total_ocr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_save_screenshot():
    print("\nTesting Save Screenshot Function...")
    print("=" * 50)
    
    try:
        from core.database import DatabaseManager
        
        db = DatabaseManager("data/tracking.db")
        
        # Test data
        test_data = {
            'file_path': 'test_screenshots/test.png',
            'timestamp': datetime.now().isoformat(),
            'window_title': 'Test Window',
            'app_name': 'Test App'
        }
        
        print("🔄 Attempting to save test screenshot...")
        screenshot_id = db.save_screenshot(
            test_data['file_path'],
            test_data['timestamp'],
            test_data['window_title'],
            test_data['app_name']
        )
        
        if screenshot_id:
            print(f"✅ Screenshot saved successfully with ID: {screenshot_id}")
            
            # Test OCR save
            print("🔄 Testing OCR result save...")
            ocr_success = db.save_ocr_result(
                screenshot_id,
                "This is test OCR text",
                95.5,
                5
            )
            
            if ocr_success:
                print("✅ OCR result saved successfully")
            else:
                print("❌ OCR result save failed")
            
            return True
        else:
            print("❌ Screenshot save failed - returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error in save screenshot test: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return False

def test_database_schema():
    print("\nTesting Database Schema...")
    print("=" * 50)
    
    try:
        import sqlite3
        
        conn = sqlite3.connect("data/tracking.db")
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("Available tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print(f"    Columns:")
            for col in columns:
                print(f"      {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Schema check error: {e}")
        return False

def test_manual_insert():
    print("\nTesting Manual Database Insert...")
    print("=" * 50)
    
    try:
        import sqlite3
        
        conn = sqlite3.connect("data/tracking.db")
        cursor = conn.cursor()
        
        # Try direct insert
        cursor.execute("""
        INSERT INTO screenshots (file_path, timestamp, window_title, app_name)
        VALUES (?, ?, ?, ?)
        """, ('manual_test.png', datetime.now().isoformat(), 'Manual Test', 'Test App'))
        
        # Get the ID
        screenshot_id = cursor.lastrowid
        print(f"✅ Manual insert successful, ID: {screenshot_id}")
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Manual insert error: {e}")
        return False

def main():
    print("🔧 Database Diagnostic Tool")
    print("=" * 60)
    
    success = True
    
    # Test database connection
    if not test_database_connection():
        success = False
    
    # Test database schema
    if not test_database_schema():
        success = False
    
    # Test manual insert
    if not test_manual_insert():
        success = False
    
    # Test save screenshot function
    if not test_save_screenshot():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All database tests passed!")
        print("The issue might be in the app_controller logic.")
    else:
        print("❌ Database issues detected. Check the errors above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()