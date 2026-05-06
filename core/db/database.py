import sqlite3
import os
import logging
from core.db.repositories.file_repository import FileRepository
from core.db.repositories.media_repository import MediaRepository
from core.db.repositories.match_repository import MatchRepository
from core.db.repositories.cache_repository import CacheRepository
from core.db.repositories.settings_repository import SettingsRepository
from core.db.repositories.history_repository import HistoryRepository

logger = logging.getLogger(__name__)

class LibraryDB:
    """
    Core Database Manager (Facade/Unit of Work).
    Orchestrates specialized repositories and manages the SQLite connection.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'renda.db')
        
        self.db_path = db_path
        self._init_db()
        
        # Initialize Repositories
        self.files = FileRepository(self)
        self.media = MediaRepository(self)
        self.matches = MatchRepository(self)
        self.cache = CacheRepository(self)
        self.settings = SettingsRepository(self)
        self.history = HistoryRepository(self)

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.Error:
            pass
        return conn

    def _init_db(self):
        """Initializes schema and migrations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Media Items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tmdb_id INTEGER UNIQUE,
                    imdb_id TEXT,
                    title TEXT,
                    year INTEGER,
                    media_type TEXT,
                    director TEXT,
                    cast TEXT,
                    rating_tmdb REAL,
                    rating_imdb REAL,
                    rating_rotten TEXT,
                    rating_metacritic INTEGER,
                    votes_imdb INTEGER,
                    vote_count_tmdb INTEGER,
                    budget INTEGER,
                    revenue INTEGER,
                    runtime INTEGER,
                    popularity REAL,
                    tagline TEXT,
                    overview TEXT,
                    genres TEXT,
                    original_title TEXT,
                    original_language TEXT,
                    origin_country TEXT,
                    release_date TEXT,
                    first_air_date TEXT,
                    last_air_date TEXT,
                    number_of_episodes INTEGER,
                    number_of_seasons INTEGER,
                    languages TEXT,
                    status TEXT,
                    type TEXT,
                    poster_path TEXT,
                    details_json TEXT,
                    fetched_languages TEXT,
                    networks TEXT,
                    collection TEXT,
                    last_updated DATETIME
                )
            """)
            
            # 2. Physical Files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    current_path TEXT UNIQUE,
                    original_path TEXT,
                    last_path TEXT,
                    parent_file_id INTEGER,
                    category TEXT,
                    file_name TEXT,
                    extension TEXT,
                    size_bytes INTEGER,
                    media_type TEXT,
                    status TEXT DEFAULT 'new',
                    part_number INTEGER,
                    language TEXT,
                    sub_category TEXT,
                    nfo_imdb_id TEXT,
                    internal_title TEXT,
                    duration REAL,
                    resolution TEXT,
                    video_codec TEXT,
                    video_bitrate INTEGER,
                    framerate TEXT,
                    bit_depth INTEGER,
                    hdr_type TEXT,
                    audio_codec TEXT,
                    audio_channels TEXT,
                    audio_bitrate INTEGER,
                    audio_streams_json TEXT,
                    subtitle_streams_json TEXT,
                    technical_json TEXT,
                    fn_title TEXT,
                    fn_year INTEGER,
                    fn_season INTEGER,
                    fn_episode TEXT,
                    fn_media_type TEXT,
                    fd_title TEXT,
                    fd_year INTEGER,
                    fd_season INTEGER,
                    fd_episode TEXT,
                    fd_media_type TEXT,
                    match_status TEXT DEFAULT 'pending',
                    previous_match_status TEXT,
                    edition TEXT,
                    is_manual INTEGER DEFAULT 0,
                    target_language TEXT,
                    part TEXT,
                    FOREIGN KEY(parent_file_id) REFERENCES media_files(id)
                )
            """)

            # 3. Junctions & History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_media_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    media_item_id INTEGER,
                    tv_episode_id INTEGER,
                    FOREIGN KEY(file_id) REFERENCES media_files(id),
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id),
                    UNIQUE(file_id, media_item_id, tv_episode_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    tmdb_id INTEGER,
                    title TEXT,
                    year INTEGER,
                    media_type TEXT,
                    poster_path TEXT,
                    source TEXT,
                    FOREIGN KEY(file_id) REFERENCES media_files(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tv_seasons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tmdb_id INTEGER UNIQUE,
                    media_item_id INTEGER,
                    season_number INTEGER,
                    name TEXT,
                    overview TEXT,
                    poster_path TEXT,
                    air_date TEXT,
                    episode_count INTEGER,
                    details_json TEXT,
                    fetched_languages TEXT,
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id),
                    UNIQUE(media_item_id, season_number)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tv_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tmdb_id INTEGER UNIQUE,
                    imdb_id TEXT,
                    season_id INTEGER,
                    media_item_id INTEGER,
                    season_number INTEGER,
                    episode_number INTEGER,
                    name TEXT,
                    overview TEXT,
                    air_date TEXT,
                    runtime INTEGER,
                    still_path TEXT,
                    vote_average REAL,
                    vote_count_tmdb INTEGER,
                    rating_imdb REAL,
                    votes_imdb INTEGER,
                    rating_rotten TEXT,
                    rating_metacritic INTEGER,
                    details_json TEXT,
                    fetched_languages TEXT,
                    FOREIGN KEY(season_id) REFERENCES tv_seasons(id),
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id),
                    UNIQUE(media_item_id, season_number, episode_number)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rename_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT,
                    file_id INTEGER,
                    old_path TEXT,
                    new_path TEXT,
                    timestamp DATETIME,
                    FOREIGN KEY(file_id) REFERENCES media_files(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON media_files(match_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_file ON file_media_links(file_id)")
            
            conn.commit()

    # --- Backward Compatibility Wrappers (to avoid breaking the whole app at once) ---
    def get_file_by_id(self, fid): return self.files.get_file_by_id(fid)
    def get_file_by_path(self, path): return self.files.get_file_by_path(path)
    def update_file(self, fid, **kwargs): self.files.update_file(fid, **kwargs)
    def get_api_cache(self, key): return self.cache.get(key)
    def set_api_cache(self, key, data): self.cache.set(key, data)
    def delete_api_cache(self, key): self.cache.delete(key)
    def get_links_for_file(self, fid): return self.media.get_links_for_file(fid)
    def get_media_item_by_id(self, mid): return self.media.get_media_item_by_id(mid)
    def get_candidates(self, fid): return self.matches.get_candidates(fid)
    def get_history(self, limit=100): return self.history.get_recent(limit)
    
    def wipe_discovery_data(self):
        """Clears all data except settings."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM media_files")
            conn.execute("DELETE FROM media_items")
            conn.execute("DELETE FROM file_media_links")
            conn.execute("DELETE FROM tv_seasons")
            conn.execute("DELETE FROM tv_episodes")
            conn.execute("DELETE FROM rename_history")
            conn.execute("DELETE FROM match_candidates")
            conn.execute("DELETE FROM api_cache")
            conn.commit()
    # ... add more wrappers as needed or refactor callers to use .files, .media etc.
