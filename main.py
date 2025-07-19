from api_client import APIClient
from config import Config
from file_ops import get_vid_files_all, rename_vid_files
from meta import extract_metadata
from movie_handler import normalize_movies, handle_movie_no, handle_movie_mult


def main():

    config = Config()
    config_data = config.get_config()

    folder_path = config_data["folder_path"]
    recursive = config_data["recursive"]
    api_source = config_data["api_source"]
    movie_template = config_data["movie_template"]
    episode_template = config_data["episode_template"]
    zero_padding = config_data["zero_padding"]
    live_run = config_data["live_run"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    video_files = get_vid_files_all(folder_path, recursive)

    movie_one, movie_no, movie_mult, episode_one, episode_no, episode_mult, unknown_files = extract_metadata(video_files, api_client, api_source)

    handled_movie_no, skipped_movie_no = handle_movie_no(movie_no, api_client, api_source)
    handled_movie_mult, skipped_movie_mult = handle_movie_mult(movie_mult, api_client, api_source)

    norm_movie_one = normalize_movies(movie_one)
    norm_movie_no = normalize_movies(handled_movie_no)
    norm_movie_mult = normalize_movies(handled_movie_mult)

    movies = norm_movie_one + norm_movie_no + norm_movie_mult
    
    rename_vid_files(movies, live_run, zero_padding, movie_template, episode_template)





if __name__ == "__main__":
    main()
