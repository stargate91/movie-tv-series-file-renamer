import json
from core.db.repositories.base_repository import BaseRepository

class CacheRepository(BaseRepository):
    """
    Handles API response caching.
    """
    def get(self, key):
        with self._get_connection() as conn:
            row = conn.execute("SELECT response_json FROM api_cache WHERE cache_key = ?", (key,)).fetchone()
            return json.loads(row['response_json']) if row else None

    def set(self, key, data):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO api_cache (cache_key, response_json, timestamp)
                VALUES (?, ?, datetime('now'))
            """, (key, json.dumps(data, ensure_ascii=False)))
            conn.commit()

    def delete(self, key):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (key,))
            conn.commit()

    def clear_all(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM api_cache")
            conn.commit()
