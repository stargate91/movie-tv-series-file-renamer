from dotenv import load_dotenv
from build import DEFAULT_CONFIG, KEYS_ERROR_MESSAGE
import os
import argparse
import configparser
import sys

class Config:
    def __init__(self):
        self.DEFAULT_CONFIG = DEFAULT_CONFIG

        self.config = configparser.ConfigParser()

        self.run_dir = self.get_run_dir()
        self.config_path = os.path.join(self.run_dir, "config.ini")

        if not os.path.exists(self.config_path):
            self.create_default_config()

        self.config.read(self.config_path)

        dotenv_path = os.path.join("data", ".env")
        load_dotenv(dotenv_path)

        self.omdb_key = os.getenv('OMDB_KEY', self.config.get('API', 'omdb_key', fallback=None))
        self.tmdb_key = os.getenv('TMDB_KEY', self.config.get('API', 'tmdb_key', fallback=None))
        self.tmdb_bearer_token = os.getenv('TMDB_BEARER_TOKEN', self.config.get('API', 'tmdb_bearer_token', fallback=None))

        self.args = self.parse_args()

        self.source = "config.ini"
        if any(vars(self.args).values()):
            self.source = "argparse"

    def get_run_dir(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def create_default_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(self.DEFAULT_CONFIG)
        print(f"[INFO] Default config.ini created at {self.config_path}")

    def validate_api_keys(self):
        placeholders = {"your_omdb_key_here", "your_tmdb_key_here", "your_tmdb_token_here"}

        if not all([self.omdb_key, self.tmdb_key, self.tmdb_bearer_token]):
            print("\n[ERROR] Missing API key(s) or token.")
            self._print_key_error_and_exit()

        if (self.omdb_key in placeholders or
            self.tmdb_key in placeholders or
            self.tmdb_bearer_token in placeholders):
            print("\n[ERROR] You are still using placeholder API keys. Please replace them with real keys!")
            self._print_key_error_and_exit()

    def _print_key_error_and_exit(self):
        print(KEYS_ERROR_MESSAGE)
        input("[INFO] Press Enter to exit...")
        sys.exit(1)

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description="Automatically renames video files based on metadata."
        )
        parser.add_argument("--folder", help="Path to the folder containing the movie files to rename.")
        parser.add_argument("--vid_size", type=int, help="Set the minimum size of video files for processing.")
        parser.add_argument("--recursive", action="store_true", help="Include video files in subdirectories recursively.")
        parser.add_argument("--source", help="Which database to use for searching ('omdb' or 'tmdb').", choices=["omdb", "tmdb"])
        parser.add_argument("--movie_template", help="The template used for renaming movie files")
        parser.add_argument("--episode_template", help="The template used for renaming episode files")
        parser.add_argument("--zero-padding", action="store_true", help="Use zero-padding for season and episode numbers (S01E01).")
        parser.add_argument("--live-run", action="store_true", help="Perform the actual renaming, modifying files.")
        parser.add_argument("--use-emojis", action="store_true", help="Enable emoji icons in terminal output for better readability.")
        return parser.parse_args()

    def get_config(self):
        folder_path = self.args.folder if self.args.folder else self.config.get('GENERAL', 'folder_path', fallback=None)
        if folder_path is None:
            raise ValueError("No folder path provided. Use --folder or set it in config.ini.")

        vid_size = self.args.vid_size if self.args.vid_size else self.config.getint('GENERAL', 'vid_size', fallback=None)
        if vid_size is None:
            raise ValueError("No video size provided. Use --vid_size or set it in config.ini.")

        recursive = self.config.getboolean('GENERAL', 'recursive', fallback=False)
        source = self.config.get('GENERAL', 'source', fallback='tmdb')
        live_run = self.config.getboolean('GENERAL', 'live_run', fallback=False)
        zero_padding = self.config.getboolean('TEMPLATES', 'zero_padding', fallback=False)
        use_emojis = self.config.getboolean('GENERAL', 'use_emojis', fallback=False)

        if self.args.recursive:
            recursive = True
        if self.args.live_run:
            live_run = True
        if self.args.zero_padding:
            zero_padding = True
        if self.args.use_emojis:
            use_emojis = True

        movie_template = self.config.get('TEMPLATES', 'movie_template', fallback="{movie_title} {movie_year}-{resolution}")
        episode_template = self.config.get('TEMPLATES', 'episode_template', fallback="{series_title} - S{season}E{episode} - {episode_title}-{air_date}-{resolution}")

        return {
            "folder_path": folder_path,
            "vid_size": vid_size,
            "recursive": recursive,
            "api_source": source,
            "movie_template": movie_template,
            "episode_template": episode_template,
            "zero_padding": zero_padding,
            "live_run": live_run,
            "use_emojis": use_emojis,
            "omdb_key": self.omdb_key,
            "tmdb_key": self.tmdb_key,
            "tmdb_bearer_token": self.tmdb_bearer_token
        }

