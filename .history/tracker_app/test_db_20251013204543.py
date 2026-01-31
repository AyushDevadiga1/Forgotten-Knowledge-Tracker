conn = sqlite3.connect(DB_PATH)
print([row for row in conn.execute("SELECT * FROM sessions LIMIT 5")])
conn.close()
