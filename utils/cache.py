import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DataStore:
    """SQLite-based unified key-value store for cache and settings."""
    
    _db_path = None
    _connection = None

    @classmethod
    def get_connection(cls):
        if cls._connection is None:
            data_dir = "data"
            os.makedirs(data_dir, exist_ok=True)
            cls._db_path = os.path.join(data_dir, "app_data.db")
            cls._connection = sqlite3.connect(cls._db_path, check_same_thread=False)
            cls._create_table()
        return cls._connection

    @classmethod
    def _create_table(cls):
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                category TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (category, key)
            )
        ''')
        conn.commit()

    def __init__(self, category="default"):
        self.category = category.replace('.json', '')  # Legacy support for old names
        self.conn = self.get_connection()

    def get(self, key):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM kv_store WHERE category=? AND key=?", (self.category, key))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return None
        return None

    def set(self, key, value):
        cursor = self.conn.cursor()
        try:
            val_str = json.dumps(value)
            cursor.execute('''
                INSERT OR REPLACE INTO kv_store (category, key, value) 
                VALUES (?, ?, ?)
            ''', (self.category, key, val_str))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving to cache ({self.category}:{key}): {e}")

    def get_keys(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT key FROM kv_store WHERE category=? ORDER BY key DESC", (self.category,))
        return [row[0] for row in cursor.fetchall()]

    def delete(self, key):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kv_store WHERE category=? AND key=?", (self.category, key))
        self.conn.commit()
