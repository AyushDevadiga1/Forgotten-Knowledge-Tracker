# tests/cleanup_test_data.py
import sqlite3
from core.db_module import DB_PATH

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Delete test sessions
c.execute("DELETE FROM sessions WHERE app_name LIKE 'TEST_%';")
# Delete test multi-modal logs
c.execute("DELETE FROM multi_modal_logs WHERE window_title LIKE 'TEST_%';")
# Delete test memory decay data
c.execute("DELETE FROM memory_decay WHERE keyword LIKE 'TEST_%';")
# Delete test metrics/reminders
c.execute("DELETE FROM metrics WHERE concept LIKE 'TEST_%';")

conn.commit()
conn.close()

print("All test data with 'TEST_' tag removed successfully! ✅")
