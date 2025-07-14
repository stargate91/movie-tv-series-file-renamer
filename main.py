from cli import parse_args
from file_ops import get_video_files, rename_files, handle_multiple_movie_results, handle_no_results, handling_series
from meta import process_video_files, transfer_metadata_to_api
from api import APIClient
from dotenv import load_dotenv
import os

def main():
    args = parse_args()
    folder_path = args.folder
    recursive = args.recursive
    meta = args.meta
    api_source = args.source
    file_type = args.type
    second_meta = args.second
    dry_run = args.dry_run

    load_dotenv()

    omdb_key = os.getenv('OMDB_KEY')
    tmdb_key = os.getenv('TMDB_KEY')
    tmdb_bearer_token = os.getenv('TMDB_BEARER_TOKEN')

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

    video_files = get_video_files(folder_path, recursive)
    
    processed_files = process_video_files(video_files, meta, file_type)

    no_results, one_result, multiple_results = transfer_metadata_to_api(processed_files, api_client, api_source, file_type)

    handling_series(one_result)


    '''if second_meta and meta == "file":
        no_results_paths = [file_data['file_path'] for file_data in no_results]

        second_processed_files = process_video_files(no_results_paths, "folder", file_type)
        no_results, second_one_result, second_multiple_results = transfer_metadata_to_api(second_processed_files, api_client, api_source, file_type)
        one_result += second_one_result
        multiple_results += second_multiple_results
    if second_meta and meta == "folder":
        second_processed_files = process_video_files(no_results, "file", file_type)
        no_results, second_one_result, second_multiple_results = transfer_metadata_to_api(second_processed_files, api_client, api_source, file_type)
        one_result += second_one_result
        multiple_results += second_multiple_results


    rename_files(one_result, dry_run)
    handled_files = handle_multiple_movie_results(multiple_results)
    rename_files(handled_files, dry_run)
    manually_handled_files = handle_no_results(no_results, api_client, api_source)
    rename_files(manually_handled_files, dry_run)'''



if __name__ == "__main__":
    main()
