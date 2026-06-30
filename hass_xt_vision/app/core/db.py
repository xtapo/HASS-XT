import sqlite3
import os
from typing import List, Dict, Any

class HistoryDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Ensure parent directories exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        print(f"[Database] Initializing history database at {self.db_path}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    image_filename TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    error_message TEXT
                )
            """)
            conn.commit()

    def add_entry(self, timestamp: str, entity_id: str, image_filename: str, description: str, status: str, error_message: str = "") -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO history (timestamp, entity_id, image_filename, description, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (timestamp, entity_id, image_filename, description, status, error_message))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[Database] Error adding history entry: {e}")
            return -1

    def get_entries(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, entity_id, image_filename, description, status, error_message
                    FROM history
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[Database] Error fetching history entries: {e}")
            return []

    def delete_entry(self, entry_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM history WHERE id = ?", (entry_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Database] Error deleting history entry {entry_id}: {e}")
            return False

    def clear_history(self) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM history")
                conn.commit()
                return True
        except Exception as e:
            print(f"[Database] Error clearing history: {e}")
            return False
