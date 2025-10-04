import sqlite3

# Connect to the database in the same folder
conn = sqlite3.connect("sessions.db")
cursor = conn.cursor()

# Show the rows after id 195
print("Rows with id > 195:")
cursor.execute("SELECT * FROM sessions WHERE id > 195")
rows = cursor.fetchall()
for row in rows:
    print(row)

# Ask which id to delete
row_id_to_delete = input("\nEnter the ID you want to delete: ")
try:
    row_id_to_delete = int(row_id_to_delete)
    cursor.execute("DELETE FROM sessions WHERE id = ?", (row_id_to_delete,))
    conn.commit()
    print(f"Row with ID {row_id_to_delete} deleted successfully!")
except ValueError:
    print("Please enter a valid integer ID.")
except sqlite3.Error as e:
    print("SQLite error:", e)

# Close the connection
conn.close()
