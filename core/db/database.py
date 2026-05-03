import sqlite3
import os
import json
from datetime import datetime

class LibraryDB:
    """
    Core Database Manager for v3.0 (The Pocket Library Foundation).
    Handles persistence of files, metadata, and relations.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            # Use local data folder in project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            db_path = os.path.join(data_dir, 'renda.db')
        
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        # Increased timeout to 30s to handle concurrent writes better
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency (Write-Ahead Logging)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.Error:
            pass
            
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
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
                    last_updated DATETIME
                )
            """)
            
            # Migration: Add columns if they don't exist
            try:
                cursor.execute("ALTER TABLE media_items ADD COLUMN director TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN cast TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN rating_tmdb REAL")
                cursor.execute("ALTER TABLE media_items ADD COLUMN rating_imdb REAL")
                cursor.execute("ALTER TABLE media_items ADD COLUMN rating_rotten TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN rating_metacritic INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN votes_imdb INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN vote_count_tmdb INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN budget INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN revenue INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN runtime INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN popularity REAL")
                cursor.execute("ALTER TABLE media_items ADD COLUMN tagline TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN overview TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN genres TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN original_title TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN original_language TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN origin_country TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN release_date TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN first_air_date TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN last_air_date TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN number_of_episodes INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN number_of_seasons INTEGER")
                cursor.execute("ALTER TABLE media_items ADD COLUMN languages TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN status TEXT")
                cursor.execute("ALTER TABLE media_items ADD COLUMN type TEXT")
            except:
                pass

            # 2. Physical Files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    -- Path tracking
                    current_path TEXT UNIQUE,
                    original_path TEXT,
                    last_path TEXT,
                    
                    -- Relationships
                    parent_file_id INTEGER,
                    
                    -- Scanner basics
                    category TEXT,
                    file_name TEXT,
                    extension TEXT,
                    size_bytes INTEGER,
                    media_type TEXT,
                    status TEXT DEFAULT 'new',
                    part_number INTEGER,
                    language TEXT,
                    sub_category TEXT,
                    
                    -- NFO source
                    nfo_imdb_id TEXT,
                    
                    -- FFmpeg: internal title
                    internal_title TEXT,
                    
                    -- FFmpeg: video
                    duration REAL,
                    resolution TEXT,
                    video_codec TEXT,
                    video_bitrate INTEGER,
                    framerate TEXT,
                    bit_depth INTEGER,
                    hdr_type TEXT,
                    
                    -- FFmpeg: audio (primary stream summary)
                    audio_codec TEXT,
                    audio_channels TEXT,
                    audio_bitrate INTEGER,
                    
                    -- FFmpeg: full streams dump
                    audio_streams_json TEXT,
                    subtitle_streams_json TEXT,
                    technical_json TEXT,
                    
                    -- GuessIt: from filename
                    fn_title TEXT,
                    fn_year INTEGER,
                    fn_season INTEGER,
                    fn_episode TEXT,
                    fn_media_type TEXT,
                    
                    -- GuessIt: from foldername
                    fd_title TEXT,
                    fd_year INTEGER,
                    fd_season INTEGER,
                    fd_episode TEXT,
                    fd_media_type TEXT,
                    
                    -- Match result
                    match_status TEXT DEFAULT 'pending',
                    
                    -- User Overrides / Editions
                    edition TEXT,
                    
                    FOREIGN KEY(parent_file_id) REFERENCES media_files(id)
                )
            """)
            
            # Migration for edition
            try:
                cursor.execute("ALTER TABLE media_files ADD COLUMN edition TEXT")
            except:
                pass

            # 2.5 Many-to-Many Links (File -> Media / Episodes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_media_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    media_item_id INTEGER,
                    tv_episode_id INTEGER,
                    FOREIGN KEY(file_id) REFERENCES media_files(id),
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id),
                    FOREIGN KEY(tv_episode_id) REFERENCES tv_episodes(id),
                    UNIQUE(file_id, media_item_id, tv_episode_id)
                )
            """)

            # 3. Match Candidates (for MULTIPLE results awaiting user decision)
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

            # 5. API Cache (Replacing JSON DataStore)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. TV Seasons
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
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id),
                    UNIQUE(media_item_id, season_number)
                )
            """)
            
            # Migration for seasons
            try:
                cursor.execute("ALTER TABLE tv_seasons ADD COLUMN tmdb_id INTEGER")
                cursor.execute("ALTER TABLE tv_seasons ADD COLUMN episode_count INTEGER")
            except:
                pass

            # 5. TV Episodes
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
                    FOREIGN KEY(season_id) REFERENCES tv_seasons(id),
                    FOREIGN KEY(media_item_id) REFERENCES media_items(id),
                    UNIQUE(media_item_id, season_number, episode_number)
                )
            """)
            
            # Migration for episodes
            try:
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN imdb_id TEXT")
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN tmdb_id INTEGER")
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN vote_count_tmdb INTEGER")
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN rating_imdb REAL")
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN votes_imdb INTEGER")
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN rating_rotten TEXT")
                cursor.execute("ALTER TABLE tv_episodes ADD COLUMN rating_metacritic INTEGER")
            except:
                pass

            # 6. Rename History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rename_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER,
                    old_path TEXT,
                    new_path TEXT,
                    timestamp DATETIME,
                    FOREIGN KEY(file_id) REFERENCES media_files(id)
                )
            """)

            # 7. User Settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            
            conn.commit()

    # ── Scanner operations ──────────────────────────────────────

    def add_file(self, path, category, size_bytes, media_type='unknown', sub_category=None):
        """Inserts or updates a file in the database."""
        name = os.path.basename(path)
        ext = os.path.splitext(path)[1].lower()
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO media_files (current_path, original_path, last_path, category, file_name, extension, size_bytes, media_type, sub_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(current_path) DO UPDATE SET
                    size_bytes = excluded.size_bytes,
                    category = excluded.category,
                    sub_category = COALESCE(excluded.sub_category, media_files.sub_category)
            """, (path, path, path, category, name, ext, size_bytes, media_type, sub_category))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def link_parent(self, file_id, parent_id):
        """Links a child file (subtitle/extra) to a parent video file."""
        conn = self._get_connection()
        try:
            conn.execute("UPDATE media_files SET parent_file_id = ? WHERE id = ?", (parent_id, file_id))
            conn.commit()
        finally:
            conn.close()

    # ── Collector operations ────────────────────────────────────

    def update_file(self, file_id, **kwargs):
        """Updates arbitrary columns on a media_files row."""
        if not kwargs:
            return
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [file_id]
        
        conn = self._get_connection()
        try:
            conn.execute(f"UPDATE media_files SET {cols} WHERE id = ?", vals)
            conn.commit()
        finally:
            conn.close()

    def bulk_update_files(self, updates_list):
        """Updates multiple media_files rows in a single transaction.
        Each dictionary in updates_list must contain an 'id' key."""
        if not updates_list:
            return
            
        conn = self._get_connection()
        try:
            for update in updates_list:
                file_id = update.pop('id')
                if not update:
                    continue
                cols = ", ".join(f"{k} = ?" for k in update)
                vals = list(update.values()) + [file_id]
                conn.execute(f"UPDATE media_files SET {cols} WHERE id = ?", vals)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_files_by_category(self, *categories):
        """Returns files matching any of the given categories."""
        placeholders = ", ".join("?" for _ in categories)
        query = f"SELECT * FROM media_files WHERE category IN ({placeholders})"
        
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(query, categories).fetchall()]

    def get_children(self, parent_id):
        """Returns all child files linked to a parent."""
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM media_files WHERE parent_file_id = ?", (parent_id,)
            ).fetchall()]

    # ── Query operations ────────────────────────────────────────

    def get_all_files(self, category=None):
        """Returns all files, optionally filtered by category."""
        query = "SELECT * FROM media_files"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def get_file_by_id(self, file_id):
        """Returns a single file by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_files WHERE id = ?", (file_id,)).fetchone()
            return dict(row) if row else None

    def get_file_by_path(self, path):
        """Returns a single file by its current path."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_files WHERE current_path = ?", (path,)).fetchone()
            return dict(row) if row else None

    def clear_all(self):
        """Wipes all data. Use with caution."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM match_candidates")
            conn.execute("DELETE FROM file_media_links")
            conn.execute("DELETE FROM tv_episodes")
            conn.execute("DELETE FROM tv_seasons")
            conn.execute("DELETE FROM rename_history")
            conn.execute("DELETE FROM media_files")
            conn.execute("DELETE FROM media_items")

    # ── Resolver operations ─────────────────────────────────────

    def upsert_media_item(self, tmdb_id, imdb_id, title, year, media_type, details_json=None, poster_path=None, 
                          director=None, cast=None, rating_tmdb=None, rating_imdb=None, rating_rotten=None, 
                          rating_metacritic=None, votes_imdb=None, vote_count_tmdb=None, budget=None, 
                          revenue=None, runtime=None, popularity=None, tagline=None, overview=None, 
                          genres=None, original_title=None, original_language=None, origin_country=None, 
                          release_date=None, first_air_date=None, last_air_date=None, 
                          number_of_episodes=None, number_of_seasons=None, languages=None, 
                          status=None, type=None):
        """Inserts or updates a media_items record. Returns the row ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO media_items (
                    tmdb_id, imdb_id, title, year, media_type, director, cast, rating_tmdb, 
                    rating_imdb, rating_rotten, rating_metacritic, votes_imdb, vote_count_tmdb, 
                    budget, revenue, runtime, popularity, tagline, overview, genres, 
                    original_title, original_language, origin_country, release_date, 
                    first_air_date, last_air_date, number_of_episodes, number_of_seasons, 
                    languages, status, type, details_json, poster_path, last_updated
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(tmdb_id) DO UPDATE SET
                    title = excluded.title,
                    director = excluded.director,
                    cast = excluded.cast,
                    rating_tmdb = excluded.rating_tmdb,
                    rating_imdb = excluded.rating_imdb,
                    rating_rotten = excluded.rating_rotten,
                    rating_metacritic = excluded.rating_metacritic,
                    votes_imdb = excluded.votes_imdb,
                    vote_count_tmdb = excluded.vote_count_tmdb,
                    budget = excluded.budget,
                    revenue = excluded.revenue,
                    runtime = excluded.runtime,
                    popularity = excluded.popularity,
                    tagline = excluded.tagline,
                    overview = excluded.overview,
                    genres = excluded.genres,
                    original_title = excluded.original_title,
                    original_language = excluded.original_language,
                    origin_country = excluded.origin_country,
                    release_date = excluded.release_date,
                    first_air_date = excluded.first_air_date,
                    last_air_date = excluded.last_air_date,
                    number_of_episodes = excluded.number_of_episodes,
                    number_of_seasons = excluded.number_of_seasons,
                    languages = excluded.languages,
                    status = excluded.status,
                    type = excluded.type,
                    details_json = excluded.details_json,
                    poster_path = excluded.poster_path,
                    last_updated = excluded.last_updated
            """, (tmdb_id, imdb_id, title, year, media_type, director, cast, rating_tmdb, 
                  rating_imdb, rating_rotten, rating_metacritic, votes_imdb, vote_count_tmdb, 
                  budget, revenue, runtime, popularity, tagline, overview, genres, 
                  original_title, original_language, origin_country, release_date, 
                  first_air_date, last_air_date, number_of_episodes, number_of_seasons, 
                  languages, status, type, details_json, poster_path))
            conn.commit()
            # Return the actual ID (lastrowid is 0 on conflict update)
            row = conn.execute("SELECT id FROM media_items WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
            return row['id'] if row else cursor.lastrowid
        finally:
            conn.close()

    def get_media_item_by_id(self, item_id):
        """Returns a single media item by its DB ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM media_items WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None

    def link_file_to_media(self, file_id, media_item_id, match_status='matched', tv_episode_id=None):
        """Links a file to a media_items record (and optionally an episode) via the junction table."""
        conn = self._get_connection()
        try:
            # Update the match status on the file itself
            conn.execute(
                "UPDATE media_files SET match_status = ? WHERE id = ?",
                (match_status, file_id)
            )
            # Create the many-to-many link
            conn.execute("""
                INSERT OR IGNORE INTO file_media_links (file_id, media_item_id, tv_episode_id)
                VALUES (?, ?, ?)
            """, (file_id, media_item_id, tv_episode_id))
            conn.commit()
        finally:
            conn.close()

    def get_links_for_file(self, file_id):
        """Returns all API metadata links for a physical file."""
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM file_media_links WHERE file_id = ?", (file_id,)
            ).fetchall()]

    def add_candidate(self, file_id, tmdb_id, title, year, media_type, poster_path=None, source=''):
        """Adds a match candidate for a file with multiple results."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO match_candidates (file_id, tmdb_id, title, year, media_type, poster_path, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file_id, tmdb_id, title, year, media_type, poster_path, source))
            conn.commit()
        finally:
            conn.close()

    def clear_candidates(self, file_id):
        """Removes all candidates for a file."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM match_candidates WHERE file_id = ?", (file_id,))
            conn.commit()
        finally:
            conn.close()

    def get_candidates(self, file_id):
        """Returns all match candidates for a file."""
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM match_candidates WHERE file_id = ?", (file_id,)
            ).fetchall()]

    def upsert_season(self, media_item_id, season_number, name, overview, poster_path, air_date, details_json=None, tmdb_id=None, episode_count=None):
        """Inserts or updates a TV season."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tv_seasons (media_item_id, season_number, name, overview, poster_path, air_date, details_json, tmdb_id, episode_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_item_id, season_number) DO UPDATE SET
                    tmdb_id = excluded.tmdb_id,
                    name = excluded.name,
                    overview = excluded.overview,
                    episode_count = excluded.episode_count,
                    details_json = excluded.details_json
            """, (media_item_id, season_number, name, overview, poster_path, air_date, details_json, tmdb_id, episode_count))
            conn.commit()
            row = conn.execute(
                "SELECT id FROM tv_seasons WHERE media_item_id = ? AND season_number = ?",
                (media_item_id, season_number)
            ).fetchone()
            return row['id'] if row else cursor.lastrowid
        finally:
            conn.close()

    def upsert_episode(self, season_id, media_item_id, season_number, episode_number,
                       name, overview, air_date, runtime, still_path, vote_average, 
                       details_json=None, rating_imdb=None, votes_imdb=None, 
                       rating_rotten=None, rating_metacritic=None, tmdb_id=None,
                       vote_count_tmdb=None, imdb_id=None):
        """Inserts or updates a TV episode."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO tv_episodes (season_id, media_item_id, season_number, episode_number,
                    name, overview, air_date, runtime, still_path, vote_average, 
                    vote_count_tmdb, rating_imdb, votes_imdb, rating_rotten, 
                    rating_metacritic, details_json, tmdb_id, imdb_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_item_id, season_number, episode_number) DO UPDATE SET
                    tmdb_id = excluded.tmdb_id,
                    imdb_id = excluded.imdb_id,
                    name = excluded.name,
                    overview = excluded.overview,
                    air_date = excluded.air_date,
                    runtime = excluded.runtime,
                    still_path = excluded.still_path,
                    vote_average = excluded.vote_average,
                    vote_count_tmdb = excluded.vote_count_tmdb,
                    rating_imdb = excluded.rating_imdb,
                    votes_imdb = excluded.votes_imdb,
                    rating_rotten = excluded.rating_rotten,
                    rating_metacritic = excluded.rating_metacritic,
                    details_json = excluded.details_json
            """, (season_id, media_item_id, season_number, episode_number,
                  name, overview, air_date, runtime, still_path, vote_average, 
                  vote_count_tmdb, rating_imdb, votes_imdb, rating_rotten, 
                  rating_metacritic, details_json, tmdb_id, imdb_id))
            conn.commit()
        finally:
            conn.close()

    # ── User Settings ───────────────────────────────────────────

    def set_setting(self, key, value):
        """Saves a user setting."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO user_settings (setting_key, setting_value)
                VALUES (?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """, (key, value))
            conn.commit()
        finally:
            conn.close()

    def get_setting(self, key, default=None):
        """Retrieves a user setting."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT setting_value FROM user_settings WHERE setting_key = ?", (key,)).fetchone()
            return row['setting_value'] if row else default

    def get_all_settings(self):
        """Retrieves all user settings as a dictionary."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT setting_key, setting_value FROM user_settings").fetchall()
            return {row['setting_key']: row['setting_value'] for row in rows}

    # ── API Cache operations ────────────────────────────────────
    
    def get_api_cache(self, key):
        """Retrieves a cached API response if available."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT response_json FROM api_cache WHERE cache_key = ?", (key,)).fetchone()
            return json.loads(row['response_json']) if row else None

    def set_api_cache(self, key, data):
        """Stores an API response in the cache."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO api_cache (cache_key, response_json, timestamp)
                VALUES (?, ?, datetime('now'))
            """, (key, json.dumps(data, ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()

    def clear_api_cache(self):
        """Clears all cached API responses."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM api_cache")
            conn.commit()


