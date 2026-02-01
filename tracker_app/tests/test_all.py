# quick_start.py
import subprocess
import sys

def run(cmd,desc):
    print(f"\n[SETUP] {desc}...")
    try:
        res = subprocess.run([sys.executable,"-m"]+cmd,shell=False,capture_output=True,text=True)
        if res.returncode==0:
            print(f"[OK] {desc} completed successfully")
        else:
            print(f"[FAIL] {desc} failed: {res.stderr}")
            return False
    except Exception as e:
        print(f"[FAIL] {desc} error: {e}")
        return False
    return True

def main():
    steps = [
        ("Installing dependencies","install_dependencies"),
        ("Training models","train_all_models"),
        ("Starting tracker","core.tracker")
    ]
    for desc,cmd in steps:
        if not run([cmd],desc):
            print(f"[FAIL] Quick start stopped at {desc}")
            return
    print("\n[SUCCESS] Forgotten Knowledge Tracker Started Successfully!")

if __name__=="__main__":
    main()
