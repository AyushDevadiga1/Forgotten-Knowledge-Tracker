# minimal_test.py
import sys
import os

# Add core to path
sys.path.append('core')

def test_minimal():
    """Test minimal functionality without optional packages"""
    try:
        # Test basic imports
        from core.db_module import init_db, init_enhanced_db
        from config import DB_PATH, ENHANCED_DB_PATH
        
        print("✓ Basic imports work")
        
        # Create databases
        os.makedirs('data', exist_ok=True)
        init_db()
        init_enhanced_db()
        
        print("✓ Databases created")
        
        # Test file creation
        if os.path.exists(DB_PATH):
            print("✓ Original database file exists")
        if os.path.exists(ENHANCED_DB_PATH):
            print("✓ Enhanced database file exists")
            
        return True
        
    except Exception as e:
        print(f"✗ Minimal test failed: {e}")
        return False

if __name__ == "__main__":
    if test_minimal():
        print("\n🎉 Minimal setup works! You can run the tracker.")
        print("\nNote: Some advanced features may not work without all packages.")
    else:
        print("\n❌ Basic setup failed.")