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
                html_address TEXT,
                local_path TEXT,
                s3_path TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                event_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES download_records(task_id)
            )
        """)
        # Migration: add columns if they don't exist
        try:
            await db.execute("ALTER TABLE file_records ADD COLUMN html_address TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE file_records ADD COLUMN event_date DATE")
        except Exception:
            pass
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


async def create_file_record(task_id: str, file_type: str, original_url: str, html_address: str = None, event_date: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO file_records (task_id, file_type, original_url, html_address, event_date, status) VALUES (?, ?, ?, ?, ?, 'pending')""",
            (task_id, file_type, original_url, html_address, event_date)
        )
        await db.commit()
        return cursor.lastrowid


async def update_file_record(record_id: int, status: str, local_path: str = None, s3_path: str = None, error_message: str = None):
    # Build dynamic update query - only update fields that are provided (not None)
    updates = ["status = ?"]
    values = [status]

    if local_path is not None:
        updates.append("local_path = ?")
        values.append(local_path)
    if s3_path is not None:
        updates.append("s3_path = ?")
        values.append(s3_path)
    if error_message is not None:
        updates.append("error_message = ?")
        values.append(error_message)

    values.append(record_id)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            f"""UPDATE file_records SET {', '.join(updates)} WHERE id = ?""",
            values
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


async def get_all_files(search: str = None, page: int = 1, page_size: int = 20):
    """Get all downloaded files with optional filter and pagination."""
    offset = (page - 1) * page_size
    params = []

    count_query = """
        SELECT COUNT(*) FROM file_records fr
        JOIN download_records dr ON fr.task_id = dr.task_id
        WHERE (fr.status = 'downloaded' OR fr.status = 'uploaded' OR fr.status = 'skipped')
    """

    where_clause = ""
    if search:
        where_clause = " AND (dr.company_name LIKE ? OR dr.bse_scrip_code LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get total count
        count_cursor = await db.execute(count_query + where_clause, params)
        total = (await count_cursor.fetchone())[0]

        # Get paginated results
        query = f"""
            SELECT
                fr.id, fr.task_id, fr.file_type, fr.original_url, fr.html_address, fr.local_path,
                fr.s3_path, fr.status, fr.error_message, fr.event_date, fr.created_at,
                dr.company_name, dr.bse_scrip_code, dr.fy, dr.quarter
            FROM file_records fr
            JOIN download_records dr ON fr.task_id = dr.task_id
            WHERE (fr.status = 'downloaded' OR fr.status = 'uploaded' OR fr.status = 'skipped'){where_clause}
            ORDER BY fr.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "files": [dict(row) for row in rows]
        }