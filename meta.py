import os
from guessit import guessit

def extract_metadata(item):

    result = guessit(item)
    file_type = result.get('type', None)

    if file_type == "episode":
        wanted_keys = ['title', 'season', 'episode', 'year']
    elif file_type == "movie":
        wanted_keys = ['title', 'year']
    else:
        print(f"[ERROR] Unknown file type for {item}: {file_type}")

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
        if file_type == "movie":
            movie_files.append(file_data)
        if file_type == "Unknown":
            unknown_files.append(file_data)

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
            print(f"[ERROR] Incorrect arguments for API source or file type for {file_path}.")
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
                "data": data,
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
                "data": data,
                "extras": extras
        }

        if data:
            if file_type == "episode":
                if data.get("total_results") == 0:
                    print(f"No results found for {file_path}: No results in TMDB response.")
                    no_results.append(episode_no_res)
                elif data.get("total_results") == 1:
                    one_result.append(episode_res)
                    print(f"One result found for {file_path}: {data}")
                elif data.get("total_results") > 1:
                    multiple_results.append(episode_res)
                    print(f"Multiple results found for {file_path}: {data}")
                else:
                    print(f"No data found for {file_path}.")
                    no_results.append(file_data)

            if file_type == "movie":
                if api_source == "omdb":
                    if data.get("Response") == "False":
                        print(f"No results found for {file_path}: {data['Error']}")
                        no_results.append(movie_no_res)
                    elif data.get("Response") == "True":
                        one_result.append(movie_res)
                        print(f"One result found for {file_data['file_path']}: {data}")
                elif api_source == "tmdb":
                    if data.get("total_results") == 0:
                        print(f"No results found for {file_data['file_path']}: No results in TMDB response.")
                        no_results.append(movie_no_res)
                    elif data.get("total_results") == 1:
                        one_result.append(movie_res)
                        print(f"One result found for {file_data['file_path']}: {data}")
                    elif data.get("total_results") > 1:
                        multiple_results.append(movie_res)
                        print(f"Multiple results found for {file_path}: {data}")    

    return no_results, one_result, multiple_results
