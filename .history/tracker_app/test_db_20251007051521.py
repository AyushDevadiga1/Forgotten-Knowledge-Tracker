import sqlite3
import pandas as pd
from config import DB_PATH

def inspect_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    report = {}

    # ------------------ Sessions ------------------
    df_sessions = pd.read_sql("SELECT * FROM sessions", conn)
    report['sessions'] = {
        "missing_start_ts": df_sessions['start_ts'].isna().sum(),
        "missing_end_ts": df_sessions['end_ts'].isna().sum(),
        "missing_app_name": df_sessions['app_name'].isna().sum(),
        "total_rows": len(df_sessions)
    }

    # ------------------ Multi-modal Logs ------------------
    df_multi = pd.read_sql("SELECT * FROM multi_modal_logs", conn)
    multi_report = {}
    required_columns = ['session_id', 'timestamp']
    for col in required_columns:
        multi_report[f"missing_{col}_column"] = col not in df_multi.columns
    if 'session_id' in df_multi.columns:
        multi_report['invalid_session_references'] = (~df_multi['session_id'].isin(df_sessions['id'])).sum()
    multi_report['total_rows'] = len(df_multi)
    report['multi_modal_logs'] = multi_report

    # ------------------ Memory Decay ------------------
    df_decay = pd.read_sql("SELECT * FROM memory_decay", conn)
    decay_report = {}
    decay_report['missing_concept_column'] = 'concept' not in df_decay.columns
    if 'concept' in df_decay.columns:
        decay_report['missing_concept_count'] = df_decay['concept'].isna().sum()
    decay_report['total_rows'] = len(df_decay)
    report['memory_decay'] = decay_report

    # ------------------ Metrics ------------------
    df_metrics = pd.read_sql("SELECT * FROM metrics", conn)
    report['metrics'] = {"total_rows": len(df_metrics)}

    conn.close()
    return report

if __name__ == "__main__":
    from pprint import pprint
    pprint(inspect_db())
