# quick_start.py
import subprocess
import sys

def run(cmd,desc):
    print(f"\n🔧 {desc}...")
    try:
        res = subprocess.run([sys.executable,"-m"]+cmd,shell=False,capture_output=True,text=True)
        if res.returncode==0:
            print(f"✅ {desc} completed successfully")
        else:
            print(f"❌ {desc} failed: {res.stderr}")
            return False
    except Exception as e:
        print(f"❌ {desc} error: {e}")
        return False
    return True

def main():
    steps = [
        ("Installing dependencies","install_dependencies"),
        ("Training models","train_all_models.py"),
        ("Starting tracker","core.tracker")
    ]
    for desc,cmd in steps:
        if not run([cmd],desc):
            print(f"❌ Quick start stopped at {desc}")
            return
    print("\n🎉 Forgotten Knowledge Tracker Started Successfully!")

if __name__=="__main__":
    main()
