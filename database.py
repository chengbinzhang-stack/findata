import aiosqlite
from typing import Optional
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "transcripts.db")


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE NOT NULL,
                bse_scrip_code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS download_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                bse_scrip_code TEXT NOT NULL,
                fy TEXT NOT NULL,
                quarter TEXT NOT NULL,
                status TEXT NOT NULL,
                folder_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                original_url TEXT,
                local_path TEXT,
                s3_path TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES download_records(task_id)
            )
        """)
        await db.commit()


async def search_companies(query: str, limit: int = 10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT company_name, bse_scrip_code FROM companies WHERE company_name LIKE ? ORDER BY company_name LIMIT ?",
            (f"%{query}%", limit)
        )
        rows = await cursor.fetchall()
        return [{"company_name": row["company_name"], "bse_scrip_code": row["bse_scrip_code"]} for row in rows]


async def get_company_by_scrip(scrip_code: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT company_name, bse_scrip_code FROM companies WHERE bse_scrip_code = ?",
            (scrip_code,)
        )
        row = await cursor.fetchone()
        if row:
            return {"company_name": row["company_name"], "bse_scrip_code": row["bse_scrip_code"]}
        return None


async def get_company_by_name(name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT company_name, bse_scrip_code FROM companies WHERE company_name = ?",
            (name,)
        )
        row = await cursor.fetchone()
        if row:
            return {"company_name": row["company_name"], "bse_scrip_code": row["bse_scrip_code"]}
        return None


async def save_company(company_name: str, bse_scrip_code: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO companies (company_name, bse_scrip_code) VALUES (?, ?)",
            (company_name, bse_scrip_code)
        )
        await db.commit()


async def create_download_task(task_id: str, company_name: str, bse_scrip_code: str, fy: str, quarter: str, folder_path: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO download_records (task_id, company_name, bse_scrip_code, fy, quarter, status, folder_path)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (task_id, company_name, bse_scrip_code, fy, quarter, folder_path)
        )
        await db.commit()


async def update_task_status(task_id: str, status: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE download_records SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
            (status, task_id)
        )
        await db.commit()


async def get_task(task_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM download_records WHERE task_id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def create_file_record(task_id: str, file_type: str, original_url: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO file_records (task_id, file_type, original_url, status) VALUES (?, ?, ?, 'pending')""",
            (task_id, file_type, original_url)
        )
        await db.commit()
        return cursor.lastrowid


async def update_file_record(record_id: int, status: str, local_path: str = None, s3_path: str = None, error_message: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE file_records SET status = ?, local_path = ?, s3_path = ?, error_message = ? WHERE id = ?""",
            (status, local_path, s3_path, error_message, record_id)
        )
        await db.commit()


async def get_file_records(task_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM file_records WHERE task_id = ?", (task_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]