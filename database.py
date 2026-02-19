import aiosqlite

DB_NAME = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS takes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                main_msg_id INTEGER,
                original_text TEXT,
                finish_text TEXT,
                media_type TEXT DEFAULT 'text',
                file_id TEXT DEFAULT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        await db.commit()