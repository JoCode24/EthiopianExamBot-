"""
reset_db.py — Run once to delete old database and start fresh.
Usage: python reset_db.py
"""
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "exam_bot.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"Deleted: {DB_PATH}")
    print("Run: python main.py to create fresh database.")
else:
    print("No database found — nothing to delete.")