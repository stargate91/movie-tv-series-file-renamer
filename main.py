from api_client import APIClient
from config import Config
from file_ops import get_video_files, rename_movie_files, rename_episode_files
from meta import process_video_files, transfer_metadata_to_api
from movie_handler import handle_no_movie_results, handle_multiple_movie_results
from series_handler_id import handle_no_series_results, handle_one_series_result, handle_multiple_series_results
from series_handler_episode import transfer_metadata_to_api_to_get_episode


def main():

    config = Config()
    config_data = config.get_config()

    folder_path = config_data["folder_path"]
    recursive = config_data["recursive"]
    meta = config_data["meta"]
    api_source = config_data["api_source"]
    second_meta = config_data["second_meta"]
    dry_run = config_data["dry_run"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    video_files = get_video_files(folder_path, recursive)
    
    movie_files, episode_files, unknown_files = process_video_files(video_files, meta)

    no_res_movie, one_res_movie, mult_res_movie = transfer_metadata_to_api(movie_files, api_client, api_source)
    no_res_episode, one_res_episode, mult_res_episode = transfer_metadata_to_api(episode_files, api_client, api_source)

    if second_meta:
        no_res_movie_paths = [file_data['file_path'] for file_data in no_res_movie]
        no_res_episode_paths = [file_data['file_path'] for file_data in no_res_episode]

        if meta == "folder":
            item_type = "file"
        elif meta == "file":
            item_type = "folder"

        movie_files = process_video_files(no_res_movie_paths, item_type)
        episode_files = process_video_files(no_res_episode_paths, item_type)

        no_res_movie, one_res_movie_sm, mult_res_movie_sm = transfer_metadata_to_api(movie_files, api_client, api_source)
        no_res_episode, one_res_episode_sm, mult_res_episode_sm = transfer_metadata_to_api(episode_files, api_client, api_source)

        one_res_movie += one_res_movie_sm
        mult_res_movie += mult_res_movie_sm

        one_res_episode += one_res_episode_sm
        mult_res_episode += mult_res_episode_sm

    rename_movie_files(one_res_movie, dry_run)
    mult_movie_handled = handle_multiple_movie_results(mult_res_movie)
    rename_movie_files(mult_movie_handled, dry_run)
    no_movie_handled = handle_no_movie_results(no_res_movie, api_client, api_source)
    rename_movie_files(no_movie_handled, dry_run)

    one_series_handled = handle_one_series_result(one_res_episode)
    mult_series_handled = handle_multiple_series_results(mult_res_episode)
    no_series_handled = handle_no_series_results(no_res_episode, api_client)

    one_series_handled += mult_series_handled
    one_series_handled += no_series_handled
    id_handled = one_series_handled

    episodes, unknown = transfer_metadata_to_api_to_get_episode(id_handled, api_client)

    rename_episode_files(episodes, dry_run)
    print("Done.")
    print("\n Unexpected files:")
    for file_data in unknown:
        print(f"\n {file_data['file_path']} manual renaming required.")

if __name__ == "__main__":
    main()
