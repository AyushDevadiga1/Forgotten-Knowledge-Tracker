#!/usr/bin/env python3
"""
Test script to verify all packages are installed correctly
"""
try:
    import pywinctl
    print("✅ pywinctl installed")
except ImportError:
    print("❌ pywinctl not installed")

try:
    import mss
    print("✅ mss installed")
except ImportError:
    print("❌ mss not installed")

try:
    from PIL import Image
    print("✅ Pillow installed")
except ImportError:
    print("❌ Pillow not installed")

try:
    import pytesseract
    print("✅ pytesseract installed")
    
    # Test Tesseract path
    try:
        pytesseract.get_tesseract_version()
        print("✅ Tesseract OCR found")
    except:
        print("⚠️  Tesseract OCR not found in PATH")
        
except ImportError:
    print("❌ pytesseract not installed")

try:
    import flask
    print("✅ Flask installed")
except ImportError:
    print("❌ Flask not installed")

try:
    import sqlite3
    print("✅ SQLite3 available")
except ImportError:
    print("❌ SQLite3 not available")

print("\n" + "="*50)
print("Installation test completed!")