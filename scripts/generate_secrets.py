import os
from cryptography.fernet import Fernet
from pathlib import Path

def generate_fernet_key(key_path):
    """Generate a new Fernet key if it doesn't exist"""
    path = Path(key_path)
    if path.exists():
        print(f"[*] {path.name} already exists. Skipping.")
        return

    print(f"[+] Generating new {path.name}...")
    key = Fernet.generate_key()
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'wb') as f:
        f.write(key)
    
    # Set restrictive permissions (read/write for owner only) if on Unix
    if os.name != 'nt':
        os.chmod(path, 0o600)
    
    print(f"[!] Key saved to {path}")

if __name__ == "__main__":
    # Base directory for secrets (matching tracker_app/data/ config)
    BASE_DIR = Path(__file__).parent.parent / "tracker_app" / "data"
    
    generate_fernet_key(BASE_DIR / "fernet.key")
    
    print("\n[✔] Secret generation complete.")
    print("[i] Remember to add these files to your local .env if needed.")
