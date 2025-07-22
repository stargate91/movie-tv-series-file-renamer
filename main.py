from api_client import APIClient
from config import Config
from file_ops import get_vid_files_all, rename_vid_files
from meta import extract_metadata
from movie_handler import handle_movie_no, handle_movie_mult
from series_handler_id import handle_episode_no, handle_episode_mult
from series_handler_episode import extract_episode_metadata
from normalizers import normalize_movies, normalize_episodes
from ui_ux import start_msg, done_msg
import sys


def main():

    config = Config()
    config.validate_api_keys()
    config_data = config.get_config()

    folder_path = config_data["folder_path"]
    vid_size = config_data["vid_size"]
    recursive = config_data["recursive"]
    api_source = config_data["api_source"]
    movie_template = config_data["movie_template"]
    episode_template = config_data["episode_template"]
    zero_padding = config_data["zero_padding"]
    live_run = config_data["live_run"]
    use_emojis = config_data["use_emojis"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    start_msg(config.source, folder_path, use_emojis)

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    video_files = get_vid_files_all(folder_path, vid_size, recursive)

    result = extract_metadata(video_files, api_client, api_source)
    movie_one, movie_no, movie_mult, episode_one, episode_no, episode_mult, unknown_files = result

    if not any([movie_one, movie_no, movie_mult, episode_one, episode_no, episode_mult, unknown_files]):
        sys.exit(0)
    
    h_movie_no, s_movie_no, r_movie_no = handle_movie_no(movie_no, api_client, api_source)
    h_movie_mult, s_movie_mult, r_movie_mult = handle_movie_mult(movie_mult, api_client, api_source)

    n_movie_one = normalize_movies(movie_one, source="There wasn't any movie with exact match.")
    n_movie_no = normalize_movies(h_movie_no, source="There wasn't any movie required manual search.")
    n_movie_mult = normalize_movies(h_movie_mult, source="There wasn't any movie required manual selection.")

    n_movie_one = n_movie_one or []
    n_movie_one += n_movie_no or []
    n_movie_one += n_movie_mult or []
    movies = n_movie_one
    
    renamed_movie_files = rename_vid_files(movies, live_run, zero_padding, movie_template, episode_template, use_emojis)
    
    h_episode_no, s_episode_no, r_episode_no = handle_episode_no(episode_no, api_client)
    h_episode_mult, s_episode_mult, r_episode_mult = handle_episode_mult(episode_mult, api_client)

    n_episode_one, x_episodes_one = normalize_episodes(episode_one, api_client, source="There wasn't any episode with exact series match.")

    n_episode_mult, x_episodes_mult = normalize_episodes(h_episode_mult, api_client, source="There wasn't any episode required manual search.")

    n_episode_no, x_episodes_no = normalize_episodes(h_episode_no, api_client, source="There wasn't any episode required manual selection.")
    
    n_episode_one = n_episode_one or []
    n_episode_one += n_episode_no or []
    n_episode_one += n_episode_mult or []
    n_episodes = n_episode_one

    episodes, u_episodes = extract_episode_metadata(n_episodes, api_client)

    renamed_episode_files = rename_vid_files(episodes, live_run, zero_padding, movie_template, episode_template, use_emojis)

    s_movie_no = s_movie_no or []
    s_movie_no += s_movie_mult or []
    s_movie_no += s_episode_no or []
    s_movie_no += s_episode_mult or []
    skipped = s_movie_no

    r_movie_no = r_movie_no or []
    r_movie_no += r_movie_mult or []
    r_movie_no += r_episode_no or []
    r_movie_no += r_episode_mult
    remaining = r_movie_no

    x_episodes_one = x_episodes_one or []
    x_episodes_one += x_episodes_mult or []
    x_episodes_one += x_episodes_no or []
    no_episode_detail = x_episodes_one

    renamed_movie_files = renamed_movie_files or []
    renamed_movie_files += renamed_episode_files or []
    renamed_files = renamed_movie_files

    done_msg(skipped, remaining, no_episode_detail, u_episodes, renamed_files, use_emojis)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
    if getattr(sys, 'frozen', False):
        input("\n[INFO] Press Enter to exit...")
