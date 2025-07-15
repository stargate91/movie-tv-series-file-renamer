from api_client import APIClient
from config import Config
from file_ops import get_video_files, rename_movie_files, rename_series_files
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
    file_type = config_data["file_type"]
    second_meta = config_data["second_meta"]
    dry_run = config_data["dry_run"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    video_files = get_video_files(folder_path, recursive)
    
    processed_files = process_video_files(video_files, meta, file_type)

    no_res, one_res, mult_res = transfer_metadata_to_api(processed_files, api_client, api_source, file_type)

    if second_meta and file_type == "movie":
        no_res_paths = [file_data['file_path'] for file_data in no_res]
        if meta == "file":
            processed_files = process_video_files(no_res_paths, "folder", file_type)
            no_res, s_one_res, s_mult_res = transfer_metadata_to_api(processed_files, api_client, api_source, file_type)
            one_res += s_one_res
            mult_res += s_mult_res
        if meta == "folder":
            processed_files = process_video_files(no_res_paths, "file", file_type)
            no_res, s_one_res, s_mult_res = transfer_metadata_to_api(processed_files, api_client, api_source, file_type)
            one_res += s_one_res
            mult_res += s_mult_res

    if file_type == "movie":
        rename_movie_files(one_res, dry_run)
        mult_handled = handle_multiple_movie_results(mult_res)
        rename_movie_files(mult_handled, dry_run)
        no_handled = handle_no_movie_results(no_res, api_client, api_source)
        rename_movie_files(no_handled, dry_run)

    if second_meta and file_type == "series":
        no_res_paths = [file_data['file_path'] for file_data in no_res]
        if meta == "file":
            processed_files = process_video_files(no_res_paths, "folder", file_type)
            no_res, s_one_res, s_mult_res = transfer_metadata_to_api(processed_files, api_client, api_source, file_type)
            one_res += s_one_res
            mult_res += s_mult_res
        if meta == "folder":
            processed_files = process_video_files(no_res_paths, "file", file_type)
            no_res, s_one_res, s_mult_res = transfer_metadata_to_api(processed_files, api_client, api_source, file_type)
            one_res += s_one_res
            mult_res += s_mult_res

    if file_type == "series":
        no_handled = handle_no_series_results(no_res, api_client)
        one_handled = handle_one_series_result(one_res)
        mult_handled = handle_multiple_series_results(mult_res)

        one_handled += no_handled
        mult_handled += one_handled

        id_handled = mult_handled

        episodes, unknown = transfer_metadata_to_api_to_get_episode(id_handled, api_client)

        rename_series_files(episodes, dry_run)


if __name__ == "__main__":
    main()
