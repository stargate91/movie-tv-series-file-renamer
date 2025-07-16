import os
import argparse
from dotenv import load_dotenv

class Config:
    def __init__(self, env_path=None):
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        self.omdb_key = os.getenv('OMDB_KEY')
        self.tmdb_key = os.getenv('TMDB_KEY')
        self.tmdb_bearer_token = os.getenv('TMDB_BEARER_TOKEN')

        self.args = self.parse_args()

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description="Automatically renames video files based on metadata."
        )
        parser.add_argument(
            "folder",
            help="Path to the folder containing the movie files to rename."
        )
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Include video files in subdirectories recursively."
        )
        parser.add_argument(
            "--meta",
            help="Which metadata source to prioritize ('file' or 'folder').",
            choices=["file", "folder"],
            default="file"
        )
        parser.add_argument(
            "--source",
            help="Which database to use for searching ('omdb' or 'tmdb'). OMDb is the default.",
            choices=["omdb", "tmdb"],
            default="omdb"
        )
        parser.add_argument(
            "--second",
            help="To do an opposite source of metadata search after getting results from the API.",
            action="store_true"
        )
        parser.add_argument(
            "--movie_template",
            help="The template used for renaming movie files",
            default="{movie_title} {movie_year}-{resolution})"
        )
        parser.add_argument(
            "--episode_template",
            help="The template used for renaming episode files",
            default="{series_title} - S{season}E{episode} - {episode_title}-{air_date}-{resolution}"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview the planned renaming without modifying any files."
        )
        return parser.parse_args()

    def get_config(self):
        return {
            "folder_path": self.args.folder,
            "recursive": self.args.recursive,
            "meta": self.args.meta,
            "api_source": self.args.source,
            "second_meta": self.args.second,
            "movie_template": self.args.movie_template,
            "episode_template": self.args.episode_template,
            "dry_run": self.args.dry_run,
            "omdb_key": self.omdb_key,
            "tmdb_key": self.tmdb_key,
            "tmdb_bearer_token": self.tmdb_bearer_token
        }
