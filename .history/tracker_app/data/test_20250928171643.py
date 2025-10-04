import sqlite3

# Connect to the database (sessions.db in the same folder)
conn = sqlite3.connect("sessions.db")
cursor = conn.cursor()

# Example: Delete a specific row after id 195
# Replace 196 with the id of the row you want to delete
row_id_to_delete = 196
cursor.execute("DELETE FROM sessions WHERE id = ?", (row_id_to_delete,))

# Commit changes and close connection
conn.commit()
print(f"Row with id {row_id_to_delete} deleted successfully.")
conn.close()
