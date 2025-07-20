from api_client import APIClient
from config import Config
from file_ops import get_vid_files_all, rename_vid_files
from meta import extract_metadata
from movie_handler import normalize_movies, handle_movie_no, handle_movie_mult
from series_handler_id import normalize_episodes, handle_episode_no, handle_episode_mult
from series_handler_episode import extract_episode_metadata
import sys


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

    result = extract_metadata(video_files, api_client, api_source)
    movie_one, movie_no, movie_mult, episode_one, episode_no, episode_mult, unknown_files = result

    if not any([movie_one, movie_no, movie_mult, episode_one, episode_no, episode_mult, unknown_files]):
        sys.exit(0)
    
    h_movie_no, s_movie_no, r_movie_no = handle_movie_no(movie_no, api_client, api_source)
    h_movie_mult, s_movie_mult, r_movie_mult = handle_movie_mult(movie_mult, api_client, api_source)

    n_movie_one = normalize_movies(movie_one, source='movies with one result')
    n_movie_no = normalize_movies(h_movie_no, source='movies that required manual search')
    n_movie_mult = normalize_movies(h_movie_mult, source='movies that required manual selection')

    n_movie_one += n_movie_no or []
    n_movie_one += n_movie_mult or []
    movies = n_movie_one
    
    rename_vid_files(movies, live_run, zero_padding, movie_template, episode_template)
    
    h_episode_no, s_episode_no, r_episode_no = handle_episode_no(episode_no, api_client)
    h_episode_mult, s_episode_mult, r_episode_mult = handle_episode_mult(episode_mult, api_client)

    n_episode_one, u_episodes_one = normalize_episodes(episode_one, api_client, source='ep_one')

    n_episode_mult, u_episodes_mult = normalize_episodes(h_episode_mult, api_client, source='ep_mult')

    n_episode_no, u_episodes_no = normalize_episodes(h_episode_no, api_client, source='ep_no')
    
    n_episode_one += n_episode_no or []
    n_episode_one += n_episode_mult or []
    n_episodes = n_episode_one

    episodes, u_episodes = extract_episode_metadata(n_episodes, api_client)

    rename_vid_files(episodes, live_run, zero_padding, movie_template, episode_template)

if __name__ == "__main__":
    main()
