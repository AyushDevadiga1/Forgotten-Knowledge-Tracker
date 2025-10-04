# test_imports.py - PROPER IMPORT TEST

import sys
import os

def setup_environment():
    """Set up Python path correctly"""
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.join(current_dir, 'core')
    
    # Add to Python path
    sys.path.insert(0, current_dir)
    sys.path.insert(0, core_dir)
    
    print(f"✓ Added to path: {current_dir}")
    print(f"✓ Added to path: {core_dir}")
    return current_dir, core_dir

def test_imports():
    """Test importing all modules"""
    print("Testing module imports...")
    print("=" * 50)
    
    modules_to_test = [
        'db_module',
        'ocr_module', 
        'audio_module',
        'webcam_module',
        'intent_module',
        'knowledge_graph',
        'memory_model',
        'face_detection_module',
        'config'
    ]
    
    success_count = 0
    for module_name in modules_to_test:
        try:
            if module_name == 'config':
                # Config is in root directory
                import config
            else:
                # Core modules are in core directory
                module = __import__(f'core.{module_name}', fromlist=[module_name])
            print(f"✓ {module_name}")
            success_count += 1
        except ImportError as e:
            print(f"✗ {module_name}: {e}")
        except Exception as e:
            print(f"✗ {module_name} (unexpected error): {e}")
    
    print("=" * 50)
    print(f"Results: {success_count}/{len(modules_to_test)} modules imported successfully")
    return success_count == len(modules_to_test)

def test_config_constants():
    """Test if config has all required constants"""
    print("\nTesting config constants...")
    print("=" * 50)
    
    required_constants = [
        'DB_PATH', 'ENHANCED_DB_PATH', 'TRACK_INTERVAL', 'SCREENSHOT_INTERVAL',
        'AUDIO_INTERVAL', 'WEBCAM_INTERVAL', 'RETENTION_DAYS', 'MEMORY_THRESHOLD',
        'USER_ALLOW_WEBCAM', 'TESSERACT_PATH'
    ]
    
    try:
        import config
        missing = []
        for constant in required_constants:
            if not hasattr(config, constant):
                missing.append(constant)
        
        if missing:
            print("❌ Missing constants in config.py:")
            for constant in missing:
                print(f"   - {constant}")
            return False
        else:
            print("✓ All required constants found in config.py")
            return True
    except ImportError as e:
        print(f"❌ Cannot import config: {e}")
        return False

if __name__ == "__main__":
    print("FKT Module Import Test")
    print("=" * 50)
    
    # Setup environment
    current_dir, core_dir = setup_environment()
    
    # Check if core directory exists and has files
    if os.path.exists(core_dir):
        core_files = os.listdir(core_dir)
        print(f"✓ Core directory exists with {len(core_files)} files")
        print(f"  Files: {[f for f in core_files if f.endswith('.py')]}")
    else:
        print(f"❌ Core directory not found: {core_dir}")
    
    # Test imports
    imports_ok = test_imports()
    config_ok = test_config_constants()
    
    if imports_ok and config_ok:
        print("\n🎉 All tests passed! You can run the tracker.")
        print("\nRun: python -m core.tracker")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")