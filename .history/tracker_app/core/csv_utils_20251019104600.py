#core/csv)
from pathlib import Path
import pandas as pd
from datetime import datetime
import numpy as np

# Folder where CSVs will be stored
DATA_DIR = Path(__file__).parent.parent / "test_data"

def create_test_csvs():
    """Creates sample CSVs if missing."""
    DATA_DIR.mkdir(exist_ok=True)

    sessions_file = DATA_DIR / "sessions_test.csv"
    logs_file = DATA_DIR / "logs_test.csv"
    decay_file = DATA_DIR / "decay_test.csv"

    # Sample sessions CSV
    if not sessions_file.exists():
        pd.DataFrame({
            "session_id": range(1, 6),
            "user_id": [101, 102, 103, 104, 105],
            "timestamp": pd.date_range(start="2025-01-01", periods=5, freq="D")
        }).to_csv(sessions_file, index=False)

    # Sample logs CSV
    if not logs_file.exists():
        pd.DataFrame({
            "log_id": range(1, 11),
            "session_id": np.random.randint(1, 6, 10),
            "action": np.random.choice(["view", "review", "quiz"], 10),
            "timestamp": pd.date_range(start="2025-01-01", periods=10, freq="12H")
        }).to_csv(logs_file, index=False)

    # Sample decay CSV
    if not decay_file.exists():
        pd.DataFrame({
            "user_id": [101, 102, 103, 104, 105],
            "decay_rate": [0.05, 0.1, 0.07, 0.08, 0.06]
        }).to_csv(decay_file, index=False)

    print(f"Test CSVs ensured at {DATA_DIR}")
