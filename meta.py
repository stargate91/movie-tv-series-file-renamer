import os
from guessit import guessit
from outputs import unknown_file_type_message
from outputs import episode_files_success_message, movie_files_success_message, unknown_files_success_message
from outputs import incorrect_api_arguments_message
from outputs import no_result_message, one_result_message, multiple_results_tmdb_message, no_data_found_message

def extract_metadata(item):

    result = guessit(item)
    file_type = result.get('type', None)

    if file_type == "episode":
        wanted_keys = ['title', 'season', 'episode', 'year']
    elif file_type == "movie":
        wanted_keys = ['title', 'year']
    else:
        unknown_file_type_message(item, file_type)

    wanted = {key: result.get(key, 'Unknown') for key in wanted_keys}
    extras = {key: value for key, value in result.items() if key not in wanted_keys}

    return file_type, wanted, extras

def process_video_files(video_files, meta):

    movie_files = []
    episode_files = []
    unknown_files = []


    for file in video_files:
        file_name = os.path.basename(file)
        folder_name = os.path.basename(os.path.dirname(file))

        if meta == "folder":
            file_type, wanted, extras = extract_metadata(folder_name)
        else:
            file_type, wanted, extras = extract_metadata(file_name)

        file_data = {
            "file_path": file,
            "file_type": file_type,
            "wanted": wanted,
            "extras": extras
        }

        if file_type == "episode":
            episode_files.append(file_data)
            episode_files_success_message(file)
        if file_type == "movie":
            movie_files.append(file_data)
            movie_files_success_message(file)
        if file_type == "Unknown":
            unknown_files.append(file_data)
            unknown_files_success_message(file)

    return movie_files, episode_files, unknown_files

def transfer_metadata_to_api(processed_files, api_client, api_source):

    no_results = []
    one_result = []
    multiple_results = []

    for file_data in processed_files:

        file_path = file_data.get('file_path')
        file_type = file_data.get('file_type')
        wanted = file_data.get('wanted')
        extras = file_data.get('extras')

        title = wanted.get('title')
        season = wanted.get('season')
        episode = wanted.get('episode')
        year = wanted.get('year')
        
        if api_source == "omdb" and file_type == "movie":
            data = api_client.get_from_omdb(title, year)
        elif api_source == "tmdb" and file_type == "movie":
            data = api_client.get_from_tmdb_movie(title, year)
        elif file_type == "episode":
            data = api_client.get_from_tmdb_tv(title, year)
        else:
            incorrect_api_arguments_message()
            data = None

        episode_no_res = {
                "file_path": file_path,
                "file_type": file_type,
                "season": season,
                "episode": episode,
                "extras": extras
        }

        episode_res = {
                "file_path": file_path,
                "file_type": file_type,
                "season": season,
                "episode": episode,
                "series_details": data,
                "extras": extras
        }

        movie_no_res = {
                "file_path": file_path,
                "file_type": file_type,
                "extras": extras
        }

        movie_res = {
                "file_path": file_path,
                "file_type": file_type,
                "movie_details": data,
                "extras": extras
        }

        if data:
            if file_type == "episode":
                if data.get("total_results") == 0:
                    no_results.append(episode_no_res)
                    no_result_message(file_path)
                elif data.get("total_results") == 1:
                    one_result.append(episode_res)
                    one_result_message(file_path, data)
                elif data.get("total_results") > 1:
                    multiple_results.append(episode_res)
                    multiple_results_tmdb_message(file_path, data)
                else:
                    no_results.append(file_data)
                    no_data_found_message(file_path)

            if file_type == "movie":
                if api_source == "omdb":
                    if data.get("Response") == "False":
                        no_results.append(movie_no_res)
                        no_result_message(file_path)
                    elif data.get("Response") == "True":
                        one_result.append(movie_res)
                        one_result_message(file_path, data)
                elif api_source == "tmdb":
                    if data.get("total_results") == 0:
                        no_results.append(movie_no_res)
                        no_result_message(file_path)
                    elif data.get("total_results") == 1:
                        one_result.append(movie_res)
                        one_result_message(file_path, data)
                    elif data.get("total_results") > 1:
                        multiple_results.append(movie_res)
                        multiple_results_tmdb_message(file_path, data)    

    return no_results, one_result, multiple_results
