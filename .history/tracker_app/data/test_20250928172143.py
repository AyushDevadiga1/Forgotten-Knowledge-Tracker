import sqlite3

# Connect to the database
conn = sqlite3.connect("sessions.db")
cursor = conn.cursor()

# Set the starting point and limit
start_id = 195
limit = 10  # Number of rows to delete after start_id

# Preview the rows to be deleted
cursor.execute("SELECT * FROM sessions WHERE id > ? ORDER BY id ASC LIMIT ?", (start_id, limit))
rows_to_delete = cursor.fetchall()

if not rows_to_delete:
    print("No rows found to delete after ID", start_id)
else:
    print("Rows to be deleted:")
    for row in rows_to_delete:
        print(row)

    # Confirm deletion
    confirm = input("\nDo you want to delete these rows? (y/n): ").lower()
    if confirm == 'y':
        cursor.execute(
            "DELETE FROM sessions WHERE id IN (SELECT id FROM sessions WHERE id > ? ORDER BY id ASC LIMIT ?)",
            (start_id, limit)
        )
        conn.commit()
        print(f"Deleted {len(rows_to_delete)} rows.")
    else:
        print("Deletion cancelled.")

# Close connection
conn.close()
