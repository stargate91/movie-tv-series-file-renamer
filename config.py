import os
import argparse
import configparser
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()

        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        self.config.read(config_path)

        dotenv_path = os.path.join("data", ".env")
        load_dotenv(dotenv_path)

        self.omdb_key = os.getenv('OMDB_KEY', self.config.get('API', 'omdb_key', fallback=None))
        self.tmdb_key = os.getenv('TMDB_KEY', self.config.get('API', 'tmdb_key', fallback=None))
        self.tmdb_bearer_token = os.getenv('TMDB_BEARER_TOKEN', self.config.get('API', 'tmdb_bearer_token', fallback=None))

        self.args = self.parse_args()

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description="Automatically renames video files based on metadata."
        )
        parser.add_argument(
            "--folder",
            help="Path to the folder containing the movie files to rename."
        )
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Include video files in subdirectories recursively."
        )
        parser.add_argument(
            "--source",
            help="Which database to use for searching ('omdb' or 'tmdb').",
            choices=["omdb", "tmdb"]
        )
        parser.add_argument(
            "--movie_template",
            help="The template used for renaming movie files"
        )
        parser.add_argument(
            "--episode_template",
            help="The template used for renaming episode files"
        )
        parser.add_argument(
            "--zero-padding",
            action="store_true",
            help="Use zero-padding for season and episode numbers (S01E01)."
        )
        parser.add_argument(
            "--live-run",
            action="store_true",
            help="Perform the actual renaming, modifying files."
        )
        return parser.parse_args()

    def get_config(self):
        folder_path = self.args.folder if self.args.folder else self.config.get('GENERAL', 'folder_path', fallback=None)

        if folder_path is None:
            raise ValueError("No folder path provided. Use --folder or set it in config.ini.")

        recursive = self.config.getboolean('GENERAL', 'recursive', fallback=False)
        source = self.config.get('GENERAL', 'source', fallback='omdb')
        live_run = self.config.getboolean('GENERAL', 'live_run', fallback=False)

        movie_template = self.config.get('TEMPLATES', 'movie_template', fallback="{movie_title} {movie_year}-{resolution})")
        episode_template = self.config.get('TEMPLATES', 'episode_template', fallback="{series_title} - S{season}E{episode} - {episode_title}-{air_date}-{resolution}")

        zero_padding = self.config.getboolean('GENERAL', 'zero_padding', fallback=False)

        if self.args.zero_padding:
            zero_padding = True

        return {
            "folder_path": folder_path,
            "recursive": recursive,
            "api_source": source,
            "movie_template": movie_template,
            "episode_template": episode_template,
            "zero_padding": zero_padding,
            "live_run": live_run,
            "omdb_key": self.omdb_key,
            "tmdb_key": self.tmdb_key,
            "tmdb_bearer_token": self.tmdb_bearer_token
        }
