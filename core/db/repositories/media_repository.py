from core.db.repositories.base_repository import BaseRepository

class MediaRepository(BaseRepository):
    """
    Handles metadata persistence (TMDB/IMDB data) and links between files and media.
    """
    def upsert_media_item(self, **data):
        # We assume data matches table columns. Handled by orchestrator or manager.
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        update_stmt = ", ".join(f"{k} = EXCLUDED.{k}" for k in data.keys() if k != 'tmdb_id')
        
        query = f"""
            INSERT INTO media_items ({cols}, last_updated)
            VALUES ({placeholders}, datetime('now'))
            ON CONFLICT(tmdb_id) DO UPDATE SET {update_stmt}, last_updated = EXCLUDED.last_updated
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, list(data.values()))
            conn.commit()
            row = conn.execute("SELECT id FROM media_items WHERE tmdb_id = ?", (data['tmdb_id'],)).fetchone()
            return row['id'] if row else cursor.lastrowid

    def get_media_item_by_id(self, item_id):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_items WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None

    def get_media_item_by_tmdb_id(self, tmdb_id):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_items WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
            return dict(row) if row else None

    def get_all_media_items(self):
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM media_items").fetchall()
            return [dict(row) for row in rows]

    def get_count(self, media_type=None):
        query = "SELECT COUNT(*) FROM media_items"
        params = []
        if media_type:
            query += " WHERE media_type = ?"
            params.append(media_type)
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchone()[0]

    def link_file_to_media(self, file_id, media_item_id, tv_episode_id=None):
        with self._get_connection() as conn:
            if tv_episode_id:
                conn.execute("DELETE FROM file_media_links WHERE file_id = ? AND media_item_id = ? AND tv_episode_id IS NULL", (file_id, media_item_id))
            conn.execute("INSERT OR IGNORE INTO file_media_links (file_id, media_item_id, tv_episode_id) VALUES (?, ?, ?)", (file_id, media_item_id, tv_episode_id))
            conn.commit()

    def get_links_for_file(self, file_id):
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM file_media_links WHERE file_id = ?", (file_id,)).fetchall()]

    # --- Seasons & Episodes ---
    def upsert_season(self, **data):
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        update_stmt = ", ".join(f"{k} = EXCLUDED.{k}" for k in data.keys() if k not in ('media_item_id', 'season_number'))
        query = f"INSERT INTO tv_seasons ({cols}) VALUES ({placeholders}) ON CONFLICT(media_item_id, season_number) DO UPDATE SET {update_stmt}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, list(data.values()))
            conn.commit()
            row = conn.execute("SELECT id FROM tv_seasons WHERE media_item_id = ? AND season_number = ?", (data['media_item_id'], data['season_number'])).fetchone()
            return row['id'] if row else cursor.lastrowid

    def get_season_by_number_by_tmdb_id(self, tmdb_id, season_number):
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT s.* FROM tv_seasons s 
                JOIN media_items m ON s.media_item_id = m.id 
                WHERE m.tmdb_id = ? AND s.season_number = ?
            """, (tmdb_id, season_number)).fetchone()
            return dict(row) if row else None

    def upsert_episode(self, **data):
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        update_stmt = ", ".join(f"{k} = EXCLUDED.{k}" for k in data.keys() if k not in ('media_item_id', 'season_number', 'episode_number'))
        query = f"INSERT INTO tv_episodes ({cols}) VALUES ({placeholders}) ON CONFLICT(media_item_id, season_number, episode_number) DO UPDATE SET {update_stmt}"
        with self._get_connection() as conn:
            conn.execute(query, list(data.values()))
            conn.commit()

    def get_episode_by_id(self, episode_id):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tv_episodes WHERE id = ?", (episode_id,)).fetchone()
            return dict(row) if row else None

    def get_season_for_episode(self, episode_id):
        with self._get_connection() as conn:
            row = conn.execute("SELECT s.* FROM tv_seasons s JOIN tv_episodes e ON e.season_id = s.id WHERE e.id = ?", (episode_id,)).fetchone()
            return dict(row) if row else None

    def get_season_by_number(self, media_item_id, season_number):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tv_seasons WHERE media_item_id = ? AND season_number = ?", (media_item_id, season_number)).fetchone()
            return dict(row) if row else None

    def get_episode_by_id_fields(self, media_item_id, season_number, episode_number):
        """Returns an episode row by its natural keys."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tv_episodes WHERE media_item_id = ? AND season_number = ? AND episode_number = ?",
                (media_item_id, season_number, episode_number)
            ).fetchone()
            return dict(row) if row else None
