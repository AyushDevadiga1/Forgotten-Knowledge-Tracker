import sqlite3

print("--- intent_validation.db data ---")
try:
    conn = sqlite3.connect('tracker_app/data/intent_validation.db')
    rows = conn.execute("SELECT user_feedback, COUNT(*) FROM intent_predictions GROUP BY user_feedback").fetchall()
    print("Feedback distribution:", rows)
    preds = conn.execute("SELECT predicted_intent, COUNT(*) FROM intent_predictions GROUP BY predicted_intent").fetchall()
    print("Prediction distribution:", preds)
except Exception as e:
    print("Error reading db:", e)
