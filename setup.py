# setup.py — FKT 2.0 — Auto-setup and single-launcher
# Run ONCE to set everything up:  python setup.py
# Then launch the full app:       python setup.py --run
#
# What this does:
#   1. Removes duplicate .venv/ (keeps venv/)
#   2. Creates venv if it doesn't exist
#   3. Installs all dependencies
#   4. Auto-downloads & installs Tesseract if missing (Windows silent install)
#   5. Creates .env from .env.example if missing
#   6. Initialises the SQLite database
#   7. With --run: starts tracker + dashboard together

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

ROOT        = Path(__file__).parent.absolute()
VENV        = ROOT / "venv"
VENV_PYTHON = VENV / "Scripts" / "python.exe"   # Windows path
TESS_URL    = (
    "https://github.com/UB-Mannheim/tesseract/releases/download/"
    "v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
)
TESS_PATH   = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def banner(msg):
    print(f"\n{'='*55}\n  {msg}\n{'='*55}")

def step(msg):  print(f"  >> {msg}")
def ok(msg):    print(f"  [OK] {msg}")
def warn(msg):  print(f"  [!]  {msg}")


def clean_duplicate_venv():
    dot = ROOT / ".venv"
    if dot.exists() and VENV.exists():
        step("Removing duplicate .venv/ (venv/ takes precedence)...")
        shutil.rmtree(dot, ignore_errors=True)
        ok(".venv/ removed.")
    elif dot.exists():
        step("Renaming .venv/ -> venv/...")
        dot.rename(VENV)
        ok("Renamed.")


def ensure_venv():
    if not VENV_PYTHON.exists():
        step("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        ok("venv created.")
    else:
        ok("venv already exists.")


def install_deps():
    req = ROOT / "requirements.txt"
    if not req.exists():
        warn("requirements.txt not found — skipping."); return
    step("Upgrading pip...")
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)
    step("Installing dependencies (may take a few minutes)...")
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(req), "-q"], check=True)
    ok("Dependencies installed.")


def ensure_tesseract():
    if shutil.which("tesseract") or TESS_PATH.exists():
        ok("Tesseract found."); return
    if sys.platform != "win32":
        warn("Tesseract not found. Install via package manager:")
        warn("  Ubuntu/Debian : sudo apt install tesseract-ocr")
        warn("  macOS         : brew install tesseract")
        return
    step("Tesseract not found — downloading Windows installer...")
    try:
        import urllib.request
        installer = ROOT / "_tess_setup.exe"
        urllib.request.urlretrieve(TESS_URL, installer)
        ok("Downloaded. Running silent install (may take ~30s)...")
        subprocess.run([str(installer), "/S", f"/D={TESS_PATH.parent}"], check=True)
        installer.unlink(missing_ok=True)
        if TESS_PATH.exists():
            ok(f"Tesseract installed at {TESS_PATH}")
        else:
            warn("Installer ran but exe not found — try manual install.")
            warn("https://github.com/UB-Mannheim/tesseract/wiki")
    except Exception as e:
        warn(f"Auto-install failed: {e}")
        warn("Download manually: https://github.com/UB-Mannheim/tesseract/wiki")


def ensure_env():
    env = ROOT / ".env"
    if env.exists():
        ok(".env exists."); return
    example = ROOT / ".env.example"
    if example.exists():
        shutil.copy(example, env)
        ok(".env created from .env.example.")
    else:
        env.write_text(
            "SECRET_KEY=change-me-before-production\n"
            "FLASK_ENV=development\nDEBUG=True\n"
            "TRACK_INTERVAL=5\nSCREENSHOT_INTERVAL=20\n"
            "AUDIO_INTERVAL=15\nWEBCAM_INTERVAL=45\n"
        )
        ok(".env created with defaults.")
    warn("Edit .env to set a strong SECRET_KEY before sharing/deploying.")


def init_db():
    step("Initialising database tables...")
    result = subprocess.run(
        [str(VENV_PYTHON), "-c",
         "from tracker_app.db.db_module import init_all_databases;"
         "init_all_databases(); print('DB_OK')"],
        cwd=str(ROOT), capture_output=True, text=True
    )
    if "DB_OK" in result.stdout:
        ok("Database ready.")
    else:
        warn(f"DB init issue: {result.stderr.strip() or result.stdout.strip()}")


def run_app():
    banner("Launching FKT 2.0")
    print("  Dashboard → http://localhost:5000")
    print("  Press Ctrl+C to stop both processes.\n")
    tracker = subprocess.Popen(
        [str(VENV_PYTHON), "-m", "tracker_app.main"], cwd=str(ROOT)
    )
    try:
        subprocess.run(
            [str(VENV_PYTHON), "-m", "tracker_app.web.app"], cwd=str(ROOT)
        )
    finally:
        tracker.terminate()
        print("\n  FKT stopped.")


def main():
    p = argparse.ArgumentParser(description="FKT 2.0 Setup & Launcher")
    p.add_argument("--run",        action="store_true", help="Launch FKT after setup")
    p.add_argument("--skip-deps",  action="store_true", help="Skip pip install step")
    p.add_argument("--skip-tess",  action="store_true", help="Skip Tesseract check")
    args = p.parse_args()

    banner("FKT 2.0 — Setup")
    clean_duplicate_venv()
    ensure_venv()
    if not args.skip_deps:  install_deps()
    if not args.skip_tess:  ensure_tesseract()
    ensure_env()
    init_db()

    banner("Setup complete")
    print("  Start FKT        :  python setup.py --run")
    print("  Start manually   :  activate venv, then:")
    print("    python -m tracker_app.main       # background tracker")
    print("    python -m tracker_app.web.app    # dashboard\n")

    if args.run:
        run_app()


if __name__ == "__main__":
    main()
