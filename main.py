from api_client import APIClient
from config import Config
from file_ops import get_vid_files_all, rename_vid_files
from meta import process_vid_files, transfer_meta_to_api
from movie_handler import handle_no_movie_results, handle_multiple_movie_results
from series_handler_id import handle_no_series_results, handle_one_series_result, handle_multiple_series_results
from series_handler_episode import transfer_metadata_to_api_to_get_episode
from outputs import done_message


def main():

    config = Config()
    config_data = config.get_config()

    folder_path = config_data["folder_path"]
    recursive = config_data["recursive"]
    meta = config_data["meta"]
    api_source = config_data["api_source"]
    movie_template = config_data["movie_template"]
    episode_template = config_data["episode_template"]
    live_run = config_data["live_run"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    video_files = get_vid_files_all(folder_path, recursive)
    
    movie_files, episode_files, unknown_files = process_vid_files(video_files, meta)

    no_res_movie, one_res_movie, mult_res_movie = transfer_meta_to_api(movie_files, api_client, api_source)
    no_res_episode, one_res_episode, mult_res_episode = transfer_meta_to_api(episode_files, api_client, api_source)

    mult_movie_handled = handle_multiple_movie_results(mult_res_movie)
    no_movie_handled = handle_no_movie_results(no_res_movie, api_client, api_source)

    one_res_movie += mult_movie_handled
    one_res_movie += no_movie_handled
    movies = one_res_movie

    one_series_handled = handle_one_series_result(one_res_episode)
    mult_series_handled = handle_multiple_series_results(mult_res_episode)
    no_series_handled = handle_no_series_results(no_res_episode, api_client)

    one_series_handled += mult_series_handled
    one_series_handled += no_series_handled
    id_handled = one_series_handled

    episodes, unknown = transfer_metadata_to_api_to_get_episode(id_handled, api_client)

    movies += episodes
    all_video_files = movies
    
    rename_vid_files(all_video_files, live_run, movie_template, episode_template)

    done_message(unknown)
    
if __name__ == "__main__":
    main()
