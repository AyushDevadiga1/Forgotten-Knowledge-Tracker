#!/usr/bin/env python
"""Check all Python files for syntax and import errors"""

import py_compile
import os
import sys
import traceback

print("=" * 70)
print("CHECKING ALL PYTHON FILES FOR ERRORS")
print("=" * 70)
print()

core_dir = "core"
errors_found = []
files_checked = 0

# Check all .py files in core directory
for filename in os.listdir(core_dir):
    if filename.endswith(".py"):
        filepath = os.path.join(core_dir, filename)
        files_checked += 1
        
        print(f"[CHECK] {filepath}...", end=" ")
        
        try:
            # Check syntax
            py_compile.compile(filepath, doraise=True)
            print("[OK]")
        except py_compile.PyCompileError as e:
            print(f"[SYNTAX ERROR]")
            errors_found.append((filepath, "Syntax Error", str(e)))
        except Exception as e:
            print(f"[ERROR]")
            errors_found.append((filepath, "Compilation Error", str(e)))

# Try importing key modules
print()
print("[IMPORT] Checking imports...")
print()

import_tests = [
    ("core.tracker", "Tracker module"),
    ("core.audio_module", "Audio module"),
    ("core.ocr_module", "OCR module"),
    ("core.db_module", "Database module"),
    ("core.knowledge_graph", "Knowledge Graph module"),
    ("core.intent_module", "Intent module"),
    ("core.memory_model", "Memory Model module"),
]

for module_name, desc in import_tests:
    try:
        print(f"[IMPORT] {desc:30s} ({module_name:30s})...", end=" ")
        __import__(module_name)
        print("[OK]")
    except Exception as e:
        print(f"[FAIL]")
        errors_found.append((module_name, "Import Error", str(e)))
        traceback.print_exc()

# Summary
print()
print("=" * 70)
print(f"FILES CHECKED: {files_checked}")
print(f"ERRORS FOUND: {len(errors_found)}")
print("=" * 70)
print()

if errors_found:
    print("ERRORS DETAILS:")
    for filepath, error_type, error_msg in errors_found:
        print()
        print(f"FILE: {filepath}")
        print(f"TYPE: {error_type}")
        print(f"MSG: {error_msg[:200]}")
else:
    print("[SUCCESS] All files passed checks!")
    print()

sys.exit(len(errors_found))
