from api_client import APIClient
from config import Config
from file_ops import get_vid_files_all, rename_vid_files
from meta import process_vid_files, transfer_meta_to_api
from movie_handler import handle_no_movie_res, handle_mult_movie_res, handle_one_movie_res
from series_handler_id import handle_no_series_res, handle_one_series_res, handle_mult_series_res
from series_handler_episode import transfer_meta_to_episde_api
from outputs import done_msg, divider1, divider2, divider3, divider4, divider5, divider6, divider7


def main():

    config = Config()
    config_data = config.get_config()

    folder_path = config_data["folder_path"]
    recursive = config_data["recursive"]
    meta = config_data["meta"]
    api_source = config_data["api_source"]
    movie_template = config_data["movie_template"]
    episode_template = config_data["episode_template"]
    zero_padding = config_data["zero_padding"]
    live_run = config_data["live_run"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    divider1()

    video_files = get_vid_files_all(folder_path, recursive)

    divider2()
    
    movie_files, episode_files, unknown_files = process_vid_files(video_files, meta)

    divider3()

    no_res_movie, one_res_movie, mult_res_movie = transfer_meta_to_api(movie_files, api_client, api_source)

    divider4()

    one_movie_handled = handle_one_movie_res(one_res_movie)

    mult_movie_handled = handle_mult_movie_res(mult_res_movie)
    no_movie_handled = handle_no_movie_res(no_res_movie, api_client, api_source)

    one_movie_handled += mult_movie_handled
    one_movie_handled += no_movie_handled
    movies = one_movie_handled

    divider5()

    rename_vid_files(movies, live_run, zero_padding, movie_template, episode_template)

    divider6()

    no_res_episode, one_res_episode, mult_res_episode = transfer_meta_to_api(episode_files, api_client, api_source)

    divider4()

    one_series_handled = handle_one_series_res(one_res_episode)
    mult_series_handled = handle_mult_series_res(mult_res_episode)
    no_series_handled = handle_no_series_res(no_res_episode, api_client)

    one_series_handled += mult_series_handled
    one_series_handled += no_series_handled
    id_handled = one_series_handled

    divider7()

    episodes, unknown = transfer_meta_to_episde_api(id_handled, api_client)

    divider4()
    
    rename_vid_files(episodes, live_run, zero_padding, movie_template, episode_template)

    done_msg(unknown)
    
if __name__ == "__main__":
    main()
