from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Optional
import os
import configparser
import logging
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
    history_file: str = ""

    # General behaviour
    interactive: bool = True
    skipped: bool = False
    recursive: bool = True
    live_run: bool = False
    undo: bool = False
    source_mode: str = "fallback"  # file | folder | fallback
    vid_size: int = 500  # minimum MB

    # Sample detection
    sample: bool = False
    sample_keywords: str = "sample,minta,trailer"
    sample_action: str = "rename"  # ignore | delete | rename
    sample_suffix: str = "sample"

    # Templates
    movie_template: str = "{custom_variable} + {movie_title} {movie_year}-{resolution}"
    episode_template: str = "{custom_variable} + {series_title} - S{season_number}E{episode_number} - {episode_title}-{air_date}-{resolution}"
    custom_variable: str = "default"
    zero_padding: bool = True
    filename_case: str = "none" # none, lower, upper, title
    separator: str = "space"   # space, dot, dash, underscore
    metadata_language: str = "en-US" # Target language
    fallback_language: str = ""      # Fallback if target is missing

    # UI
    use_emojis: bool = False

    # API keys
    omdb_key: str = ""
    tmdb_key: str = ""
    tmdb_bearer_token: str = ""

    # Filters
    video_extensions: str = ".mp4, .mkv, .avi, .mov, .wmv, .mpeg, .mpg"


from utils.cache import DataStore

class ConfigManager:
    """Centralized configuration loader/saver using SQLite."""

    def __init__(self):
        self.settings = AppSettings()
        self._store = DataStore("app")
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
        self._store.set("settings", asdict(self.settings))
        logger.info("Settings saved to DataStore.")

    def to_dict(self) -> dict:
        """Return all settings as a plain dict."""
        return asdict(self.settings)

    def _load(self) -> None:
        """Load settings from SQLite if available."""
        loaded_settings = self._store.get("settings")
        if loaded_settings:
            for fld in fields(AppSettings):
                if fld.name in loaded_settings:
                    setattr(self.settings, fld.name, loaded_settings[fld.name])


