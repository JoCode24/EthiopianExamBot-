import asyncio
import aiosqlite
import shutil
import os
from datetime import datetime

async def backup():
    from config import DATABASE_PATH
    backup_name = "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
    if os.path.exists(DATABASE_PATH):
        shutil.copy2(DATABASE_PATH, backup_name)
        print("Backup created: " + backup_name)
    else:
        print("Database not found at: " + DATABASE_PATH)

asyncio.run(backup())