import sqlite3
import pandas as pd
from config import DB_PATH

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM multi_modal_logs", conn)
conn.close()

print(df.head())
