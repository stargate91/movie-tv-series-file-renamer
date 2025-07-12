import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Automatically renames video files based on folder and file metadata (e.g., title, year, resolution)."
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
        "--type",
        help="Type of content ('movie' or 'series'). Movie is the default.",
        choices=["movie", "series"],
        default="movie"
    )
    parser.add_argument(
        "--second",
        help="To do an opposite source of metadata search, after we get the results from the api.",
        action="store_true"
    )    

    return parser.parse_args()
