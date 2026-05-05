from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Optional
import os
import configparser
import logging
from dotenv import load_dotenv
from core.exceptions import APIKeyMissingError

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    """All application settings in one typed object.
    
    The GUI reads/writes these directly.
    The CLI builds them from argparse + config.ini.
    """
    # Paths
    folder_path: str = ""
    default_scan_path: str = ""
    
    # Personalization
    user_name: str = ""
    
    # Global Organization
    move_files: bool = False
    base_target_path: str = ""
    auto_organize_by_type: bool = True # Creates "Movies" and "TV Shows" folders
    movies_subfolder_name: str = "Movies"
    shows_subfolder_name: str = "TV Shows"

    # General behaviour
    vid_size: int = 500  # minimum MB

    # Extras handling (skip, delete, rename)
    action_extra_video: str = "rename"     # Small videos (trailers, samples)
    action_extra_subtitle: str = "rename"  # Subtitle files
    action_extra_audio: str = "rename"     # Audio tracks
    action_extra_image: str = "rename"     # Posters, fanart
    action_extra_metadata: str = "rename"  # NFO, XML
    
    template_extra_video: str = "{ParentName}-trailer"
    template_extra_subtitle: str = "{ParentName}.{Language}"
    template_extra_audio: str = "{ParentName}.{Language}"
    template_extra_image: str = "poster"
    template_extra_metadata: str = "{ParentName}"

    # Sample detection
    sample: bool = False
    sample_keywords: str = "sample,minta,trailer"
    sample_action: str = "rename"  # ignore | delete | rename
    sample_suffix: str = "sample"

    # Templates (File Names)
    movie_template: str = "{Title} ({Year}) - {Resolution}"
    episode_template: str = "{ShowTitle} - {Season}{Episode} - {EpisodeTitle} - {Resolution}"
    custom_variable: str = "default"
    zero_padding: bool = True
    filename_case: str = "none" # none, lower, upper, title
    separator: str = "space"   # space, dot, dash, underscore
    
    # Folder Structure
    target_dir_movies: str = ""
    target_dir_shows: str = ""
    
    create_movie_folder: bool = True
    movie_folder_template: str = "{Title} ({Year})"
    
    create_show_folder: bool = True
    show_folder_template: str = "{ShowTitle}"
    create_season_folder: bool = True
    season_folder_template: str = "Season {Season}"
    create_episode_folder: bool = False
    episode_folder_template: str = "{ShowTitle} - {Season}{Episode}"
    
    # Extras Folder Structure (none = next to video, single = all in 1 folder, categorized = separate folders)
    extras_folder_mode: str = "none" 
    extras_folder_name: str = "Extras"
    
    # Cleanup
    cleanup_empty_folders: bool = True
    
    # Multi-part (Collision) Handling
    multi_part_position: str = "suffix"  # prefix | suffix
    multi_part_keyword: str = "Part"     # CD, Part, Disc, Disk, None
    multi_part_style: str = "number"     # number (1), zero_padded (01), roman (I), letter (A)
    multi_part_separator: str = "space"  # space, dot, dash, underscore, none
    metadata_language: str = "en-US" # Target language
    fallback_language: str = ""      # Fallback if target is missing

    # API keys
    omdb_key: str = ""
    tmdb_key: str = ""
    tmdb_bearer_token: str = ""

    # Filters & Extensions
    video_extensions: str = ".mp4, .mkv, .avi, .mov, .wmv, .flv, .webm, .m4v"
    subtitle_extensions: str = ".srt, .sub, .ass, .ssa, .vtt"
    audio_extensions: str = ".mka, .ac3, .dts, .mp3, .flac, .wav, .m4a"
    image_extensions: str = ".jpg, .jpeg, .png, .gif, .bmp, .webp"
    metadata_extensions: str = ".nfo, .xml, .txt"

import json
from core.db.database import LibraryDB

# Common Movie Editions
COMMON_EDITIONS = [
    "Director's Cut",
    "Extended Cut",
    "Extended Edition",
    "Unrated",
    "Unrated Edition",
    "Theatrical Cut",
    "Remastered",
    "Special Edition",
    "Ultimate Edition",
    "Collector's Edition",
    "Final Cut",
    "IMAX Edition",
    "Criterion Collection"
]

class ConfigManager:
    """Centralized configuration loader/saver using the v3 LibraryDB."""

    def __init__(self, db: LibraryDB = None):
        # Load environment variables from .env if present
        load_dotenv()
        self.settings = AppSettings()
        self.db = db if db else LibraryDB()
        self._load()

    def validate_api_keys(self) -> None:
        """Raise or exit if API keys are missing/placeholder."""
        placeholders = {"your_omdb_key_here", "your_tmdb_key_here", "your_tmdb_token_here", ""}
        keys = [self.settings.omdb_key, self.settings.tmdb_key, self.settings.tmdb_bearer_token]

        if not all(keys):
            logger.error("Missing API key(s) or token.")
            raise APIKeyMissingError("API Keys are missing. Please configure them in settings.")

        if any(k in placeholders for k in keys):
            logger.error("You are still using placeholder API keys. Please replace them with real keys!")
            raise APIKeyMissingError("Placeholder API keys detected. Please configure real keys in settings.")

    def save(self) -> None:
        """Persist current settings back to SQLite."""
        settings_dict = asdict(self.settings)
        for k, v in settings_dict.items():
            # Store values as JSON strings to preserve types (ints, bools)
            self.db.settings.set(k, json.dumps(v))
        logger.info("Settings saved to LibraryDB user_settings.")

    def to_dict(self) -> dict:
        """Return all settings as a plain dict."""
        return asdict(self.settings)

    def _load(self) -> None:
        """Load settings from SQLite if available, fallback to environment variables."""
        all_settings = self.db.settings.get_all()
        
        # Mapping for API keys in .env
        env_mapping = {
            "omdb_key": "OMDB_API_KEY",
            "tmdb_key": "TMDB_API_KEY",
            "tmdb_bearer_token": "TMDB_BEARER_TOKEN"
        }

        for fld in fields(AppSettings):
            # 1. Try Database first (User overrides)
            if fld.name in all_settings:
                try:
                    val = json.loads(all_settings[fld.name])
                    # Only set if not empty and not a placeholder
                    placeholders = {"your_omdb_key_here", "your_tmdb_key_here", "your_tmdb_token_here", ""}
                    if val and val not in placeholders:
                        if isinstance(val, str) and fld.name in env_mapping:
                            val = val.strip()
                        setattr(self.settings, fld.name, val)
                        continue
                except Exception:
                    pass
            
            # 2. Try .env fallback for API keys
            if fld.name in env_mapping:
                env_val = os.getenv(env_mapping[fld.name])
                if env_val:
                    setattr(self.settings, fld.name, env_val.strip())
