from core.db.repositories.base_repository import BaseRepository

class MatchRepository(BaseRepository):
    """
    Handles match candidates and pending user decisions.
    """
    def add_candidate(self, file_id, tmdb_id, title, year, media_type, poster_path=None, source=''):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO match_candidates (file_id, tmdb_id, title, year, media_type, poster_path, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_id, tmdb_id, title, year, media_type, poster_path, source))
            conn.commit()

    def get_candidates(self, file_id):
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM match_candidates WHERE file_id = ?", (file_id,)).fetchall()]

    def clear_candidates(self, file_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM match_candidates WHERE file_id = ?", (file_id,))
            conn.commit()
            
    def clear_all_for_file(self, file_id):
        """Full reset for a file: removes links and candidates."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM file_media_links WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM match_candidates WHERE file_id = ?", (file_id,))
            conn.execute("UPDATE media_files SET match_status = 'pending' WHERE id = ?", (file_id,))
            conn.commit()
