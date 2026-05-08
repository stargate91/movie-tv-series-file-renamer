import os
from core.db.repositories.base_repository import BaseRepository

class FileRepository(BaseRepository):
    """
    Handles operations related to physical files on disk (media_files table) 
    and their rename history.
    """
    def add_file(self, path, category, size_bytes, media_type='unknown', sub_category=None, language=None):
        name = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO media_files (current_path, original_path, last_path, category, file_name, extension, size_bytes, media_type, sub_category, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(current_path) DO UPDATE SET
                    size_bytes = excluded.size_bytes,
                    category = excluded.category,
                    sub_category = COALESCE(excluded.sub_category, media_files.sub_category),
                    language = COALESCE(excluded.language, media_files.language)
            """, (path, path, path, category, name, ext, size_bytes, media_type, sub_category, language))
            conn.commit()
            return cursor.lastrowid

    def update_file(self, file_id, **kwargs):
        if not kwargs: return
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [file_id]
        with self._get_connection() as conn:
            conn.execute(f"UPDATE media_files SET {cols} WHERE id = ?", vals)
            conn.commit()

    def bulk_update_files(self, updates_list):
        if not updates_list: return
        with self._get_connection() as conn:
            try:
                for update in updates_list:
                    file_id = update.get('id')
                    if file_id is None: continue
                    
                    # Create columns list excluding 'id'
                    fields = {k: v for k, v in update.items() if k != 'id'}
                    if not fields: continue
                    
                    cols = ", ".join(f"{k} = ?" for k in fields)
                    vals = list(fields.values()) + [file_id]
                    conn.execute(f"UPDATE media_files SET {cols} WHERE id = ?", vals)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

    def get_file_by_id(self, file_id):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_files WHERE id = ?", (file_id,)).fetchone()
            return dict(row) if row else None

    def get_file_by_path(self, path):
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_files WHERE current_path = ?", (path,)).fetchone()
            return dict(row) if row else None

    def get_file_by_path_insensitive(self, path):
        """Case-insensitive lookup for Windows paths."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_files WHERE current_path = ? COLLATE NOCASE", (path,)).fetchone()
            return dict(row) if row else None

    def get_files_by_category(self, *categories):
        placeholders = ", ".join("?" for _ in categories)
        query = f"SELECT * FROM media_files WHERE category IN ({placeholders})"
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(query, categories).fetchall()]

    def get_all_files(self, category=None):
        query = "SELECT * FROM media_files"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_children(self, parent_id):
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM media_files WHERE parent_file_id = ?", (parent_id,)
            ).fetchall()]

    def link_parent(self, file_id, parent_id):
        with self._get_connection() as conn:
            conn.execute("UPDATE media_files SET parent_file_id = ? WHERE id = ?", (parent_id, file_id))
            conn.commit()

    def import_all_manual(self):
        with self._get_connection() as conn:
            conn.execute("UPDATE media_files SET is_manual = 0 WHERE is_manual = 1")
            conn.commit()

    def delete_manual(self):
        with self._get_connection() as conn:
            # First clean up linked data
            conn.execute("DELETE FROM match_candidates WHERE file_id IN (SELECT id FROM media_files WHERE is_manual = 1)")
            conn.execute("DELETE FROM file_media_links WHERE file_id IN (SELECT id FROM media_files WHERE is_manual = 1)")
            conn.execute("DELETE FROM media_files WHERE is_manual = 1")
            conn.commit()

    def clear_match(self, file_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM file_media_links WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM match_candidates WHERE file_id = ?", (file_id,))
            conn.execute("UPDATE media_files SET match_status = 'pending' WHERE id = ?", (file_id,))
            conn.commit()

    def get_resolutions_for_media(self, media_item_id, season_number=None):
        with self._get_connection() as conn:
            if season_number is not None:
                query = """
                    SELECT f.resolution FROM media_files f
                    JOIN file_media_links l ON f.id = l.file_id
                    JOIN tv_episodes e ON l.tv_episode_id = e.id
                    WHERE l.media_item_id = ? AND e.season_number = ?
                """
                rows = conn.execute(query, (media_item_id, season_number)).fetchall()
            else:
                query = """
                    SELECT f.resolution FROM media_files f
                    JOIN file_media_links l ON f.id = l.file_id
                    WHERE l.media_item_id = ?
                """
                rows = conn.execute(query, (media_item_id,)).fetchall()
            return [r['resolution'] for r in rows if r['resolution']]

    def bulk_delete_files(self, file_ids):
        if not file_ids: return
        with self._get_connection() as conn:
            placeholders = ','.join(['?'] * len(file_ids))
            conn.execute(f"DELETE FROM media_files WHERE id IN ({placeholders})", file_ids)
            conn.commit()

    def delete_file(self, file_id):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM media_files WHERE id = ?", (file_id,))
            conn.commit()

    def delete_by_path_prefix(self, path_prefix):
        """Deletes all files where current_path starts with prefix."""
        with self._get_connection() as conn:
            # Match path/to/dir/*
            like_pattern = f"{path_prefix}{os.sep}%"
            conn.execute("DELETE FROM media_files WHERE current_path LIKE ?", (like_pattern,))
            # Match path/to/dir itself
            conn.execute("DELETE FROM media_files WHERE current_path = ?", (path_prefix,))
            conn.commit()

    def get_total_count(self):
        """Returns the total number of files in the library."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM media_files").fetchone()
            return row['count'] if row else 0

    def get_files_with_metadata(self, *categories):
        """Fetches files joined with their media metadata in a single efficient query."""
        placeholders = ", ".join("?" for _ in categories)
        query = f"""
            SELECT f.*, 
                   m.media_type as media_item_type, m.title as media_title, m.poster_path as media_poster,
                   e.name as episode_title, e.still_path as episode_poster,
                   s.name as season_name, s.poster_path as season_poster
            FROM media_files f
            LEFT JOIN file_media_links l ON f.id = l.file_id
            LEFT JOIN media_items m ON l.media_item_id = m.id
            LEFT JOIN tv_episodes e ON l.tv_episode_id = e.id
            LEFT JOIN tv_seasons s ON e.season_id = s.id
            WHERE f.category IN ({placeholders}) 
              AND f.status NOT IN ('renamed', 'deleted')
            GROUP BY f.id
        """
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(query, categories).fetchall()]

