from core.db.repositories.base_repository import BaseRepository

class HistoryRepository(BaseRepository):
    """
    Handles persistence of rename operations and undo history.
    """
    def get_recent(self, limit=100):
        with self._get_connection() as conn:
            return conn.execute("""
                SELECT rh.*, mf.file_name 
                FROM rename_history rh
                JOIN media_files mf ON rh.file_id = mf.id
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()

    def get_batch(self, batch_id):
        with self._get_connection() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM rename_history WHERE batch_id = ?", (batch_id,)).fetchall()]

    def add_history(self, batch_id, file_id, old_path, new_path):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO rename_history (batch_id, file_id, old_path, new_path, timestamp)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (batch_id, file_id, old_path, new_path))
            conn.commit()

    def delete_batch(self, batch_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM rename_history WHERE batch_id = ?", (batch_id,))
            conn.commit()
