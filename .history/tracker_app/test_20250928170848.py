import sqlite3

# Connect to your database
conn = sqlite3.connect("tracker.db")  # replace with your DB path
cursor = conn.cursor()

# Delete rows from 195 onward
cursor.execute("DELETE FROM sessions WHERE id >= ?", (195,))

# Commit changes
conn.commit()
conn.close()

print("Rows deleted successfully.")
