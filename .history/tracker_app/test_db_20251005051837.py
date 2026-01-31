# db_analysis.py
import sqlite3
import pandas as pd
from config import DB_PATH

def analyze_database(db_path):
    conn = sqlite3.connect(db_path)
    
    # Step 1: List all tables
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    print("Tables in DB:\n", tables, "\n")
    
    # Step 2 & 3: Inspect schemas and preview data
    for table in tables['name']:
        print(f"=== Table: {table} ===")
        
        # Schema
        schema = pd.read_sql(f"PRAGMA table_info({table})", conn)
        print("Schema:\n", schema, "\n")
        
        # Sample data
        df_sample = pd.read_sql(f"SELECT * FROM {table} LIMIT 5", conn)
        print("Sample data:\n", df_sample, "\n")
        
        # Basic stats
        df_full = pd.read_sql(f"SELECT * FROM {table}", conn)
        print("Number of rows:", len(df_full))
        print("Columns:", df_full.columns.tolist())
        print("Null values per column:\n", df_full.isnull().sum())
        print("\n" + "-"*50 + "\n")
    
    conn.close()

if __name__ == "__main__":
    analyze_database(DB_PATH)
