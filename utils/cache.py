import os
import json
import sqlite3
import logging
import threading

logger = logging.getLogger(__name__)

class DataStore:
    """SQLite-based unified key-value store for cache and settings."""
    
    _db_path = None
    _local = threading.local()

    @classmethod
    def _get_db_path(cls):
        if cls._db_path is None:
            data_dir = "data"
            os.makedirs(data_dir, exist_ok=True)
            cls._db_path = os.path.join(data_dir, "app_data.db")
        return cls._db_path

    @classmethod
    def get_connection(cls):
        if not hasattr(cls._local, 'connection'):
            path = cls._get_db_path()
            # Each thread gets its own connection
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            cls._local.connection = conn
            cls._create_table(conn)
        return cls._local.connection

    @classmethod
    def _create_table(cls, conn):
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv_store (
                category TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (category, key)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_key ON kv_store(key)')
        conn.commit()

    @classmethod
    def clear_transient_data(cls):
        """Clears only metadata, discovery and search caches. Preserves settings."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            categories_to_clear = ['file_matches', 'discovery', 'tmdb_movie_cache', 'tmdb_tv_cache', 'assets']
            cursor.execute(f"DELETE FROM kv_store WHERE category IN ({','.join(['?']*len(categories_to_clear))})", categories_to_clear)
            conn.commit()
            logger.info("Transient cache cleared successfully.")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    @classmethod
    def wipe_all_data(cls):
        """Nuclear option: Clears EVERYTHING. Use with caution."""
        conn = cls.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM kv_store')
            conn.commit()
            logger.info("Database wiped completely.")
        except Exception as e:
            logger.error(f"Error wiping database: {e}")

    def __init__(self, category="default"):
        self.category = category

    def clear_all(self):
        """Clears all data from the kv_store table for this category."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM kv_store WHERE category = ?', (self.category,))
        conn.commit()

    def get(self, key):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM kv_store WHERE category=? AND key=?", (self.category, key))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def set(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            val_str = json.dumps(value, default=str)
            cursor.execute('''
                INSERT OR REPLACE INTO kv_store (category, key, value) 
                VALUES (?, ?, ?)
            ''', (self.category, key, val_str))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving to cache ({self.category}:{key}): {e}")

    def get_blob(self, key):
        """Retrieve binary data from the store."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM kv_store WHERE category=? AND key=?", (self.category, key))
        row = cursor.fetchone()
        return row[0] if row else None

    def set_blob(self, key, blob_data):
        """Store binary data in the store."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO kv_store (category, key, value) 
                VALUES (?, ?, ?)
            ''', (self.category, key, blob_data))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving blob to cache ({self.category}:{key}): {e}")

class MediaCache:
    """Specialized cache for media files (posters, backdrops) stored as blobs in SQLite."""
    def __init__(self):
        self.store = DataStore("assets")

    def get_image(self, url):
        return self.store.get_blob(url)

    def set_image(self, url, data):
        # Ensure we are saving bytes
        if isinstance(data, (bytes, bytearray)):
            self.store.set_blob(url, data)
        else:
            try:
                self.store.set_blob(url, bytes(data))
            except Exception as e:
                logger.error(f"Failed to convert image data to bytes: {e}")

class FileMatchCache:
    """Cache for storing the final metadata pairing for a specific file."""
    def __init__(self):
        self.store = DataStore("file_matches")

    def _norm(self, path):
        if not path: return ""
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))

    def get_match(self, file_path):
        return self.store.get(self._norm(file_path))

    def set_match(self, file_path, match_data):
        self.store.set(self._norm(file_path), match_data)

    def clear(self):
        self.store.clear_all()
