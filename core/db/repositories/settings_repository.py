from core.db.repositories.base_repository import BaseRepository

class SettingsRepository(BaseRepository):
    """
    Handles user settings persistence.
    """
    def set(self, key, value):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """, (key, value))
            conn.commit()

    def set_many(self, settings_dict):
        """Bulk update settings in a single transaction."""
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT INTO user_settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """, [(k, v) for k, v in settings_dict.items()])
            conn.commit()

    def get(self, key, default=None):
        with self._get_connection() as conn:
            row = conn.execute("SELECT setting_value FROM user_settings WHERE setting_key = ?", (key,)).fetchone()
            return row['setting_value'] if row else default

    def get_all(self):
        with self._get_connection() as conn:
            rows = conn.execute("SELECT setting_key, setting_value FROM user_settings").fetchall()
            return {row['setting_key']: row['setting_value'] for row in rows}
