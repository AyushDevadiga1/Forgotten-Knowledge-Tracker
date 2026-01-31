# test_dashboard_db.py
import sqlite3
import pandas as pd
from config import DB_PATH
import networkx as nx
from core.knowledge_graph import get_graph, sync_db_to_graph

def inspect_table(table_name, sample_rows=5):
    print(f"\n=== Inspecting table: {table_name} ===")
    conn = sqlite3.connect(DB_PATH)
    try:
        # Check columns
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table_name})")
        cols = c.fetchall()
        print("Columns:")
        for col in cols:
            print(f"  {col[1]} (type: {col[2]}, not null: {col[3]}, default: {col[4]})")

        # Fetch sample data
        try:
            df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT {sample_rows}", conn)
            print(f"\nSample rows from {table_name}:")
            print(df)
        except Exception as e:
            print(f"❌ Failed to fetch rows: {e}")

    finally:
        conn.close()

def check_memory_decay():
    print("\n=== Memory Decay Validation ===")
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM memory_decay", conn)
        print("Columns:", df.columns.tolist())
        print("Null values per column:\n", df.isnull().sum())
        print("Data types:\n", df.dtypes)
        # Check if 'concept' column exists
        if 'concept' not in df.columns:
            print("❌ Missing 'concept' column, dashboard will fail.")
        # Check numeric column types
        if 'predicted_recall' in df.columns and not pd.api.types.is_numeric_dtype(df['predicted_recall']):
            print("❌ 'predicted_recall' is not numeric")
    finally:
        conn.close()

def check_metrics():
    print("\n=== Metrics Validation ===")
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql("SELECT * FROM metrics", conn)
        print("Columns:", df.columns.tolist())
        print("Null values per column:\n", df.isnull().sum())
        if 'next_review_time' in df.columns:
            df['next_review_time'] = pd.to_datetime(df['next_review_time'], errors='coerce')
            print("Converted 'next_review_time' to datetime, nulls:", df['next_review_time'].isnull().sum())
    finally:
        conn.close()

def check_graph():
    print("\n=== Knowledge Graph Validation ===")
    try:
        sync_db_to_graph()
        G = get_graph()
        print(f"Nodes: {len(G.nodes)}, Edges: {len(G.edges)}")
        if not G.nodes:
            print("❌ Graph is empty, dashboard will not display memory scores.")
        # Check node attributes
        sample_nodes = list(G.nodes(data=True))[:5]
        print("Sample node attributes:", sample_nodes)
    except Exception as e:
        print(f"❌ Failed to load/sync graph: {e}")

def main():
    tables = ["sessions", "multi_modal_logs", "memory_decay", "metrics"]
    for table in tables:
        inspect_table(table)
    check_memory_decay()
    check_metrics()
    check_graph()

if __name__ == "__main__":
    main()
