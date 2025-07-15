import re
import os
from guessit import guessit

def extract_metadata_from_filename(file_name, file_type):

    result = guessit(file_name)

    if file_type == "series":
        wanted_keys = ['title', 'season', 'episode', 'year']
    else:
        wanted_keys = ['title', 'year']

    wanted = {k: result.get(k, 'Unknown') for k in wanted_keys}
    extras = {k: v for k, v in result.items() if k not in wanted_keys}

    return wanted, extras

def extract_metadata_from_folder(folder_name, file_type):

    result = guessit(folder_name)

    if file_type == "series":
        wanted_keys = ['title', 'year']
    else:
        wanted_keys = ['title', 'year']

    wanted = {k: result.get(k, 'Unknown') for k in wanted_keys}
    extras = {k: v for k, v in result.items() if k not in wanted_keys}

    return wanted, extras

def process_video_files(video_files, meta, file_type):

    processed_files = []

    for file in video_files:
        file_name = os.path.basename(file)
        folder_name = os.path.basename(os.path.dirname(file))

        if meta == "folder":
            wanted, extras = extract_metadata_from_folder(folder_name, file_type)
        else:
            wanted, extras = extract_metadata_from_filename(file_name, file_type)

        processed_files.append({
            "file_path": file,
            "wanted": wanted,
            "extras": extras
        })

    return processed_files

def transfer_metadata_to_api(processed_files, api_client, api_source, file_type):

    no_results = []
    one_result = []
    multiple_results = []

    for file_data in processed_files:

        wanted = file_data.get('wanted')
        extras = file_data.get('extras')
        title = wanted.get('title')
        year = wanted.get('year')
        season = wanted.get('season')
        episode = wanted.get('episode')
        
        if api_source == "omdb" and file_type == "movie":
            data = api_client.get_from_omdb(title, year)
        elif api_source == "tmdb" and file_type == "movie":
            data = api_client.get_from_tmdb_movie(title, year)
        elif file_type == "series":
            data = api_client.get_from_tmdb_tv(title, year)
        else:
            print("[ERROR] Incorrect arguments for API source or file type.")
            data = None

        if data:
            if file_type == "series":
                if data.get("total_results") == 0:
                    print(f"No results found for {file_data['file_path']}: No results in TMDB response.")
                    no_results.append({
                        "file_path": file_data['file_path'],
                        "season": season,
                        "episode": episode,
                        "extras": extras
                    })
                elif data.get("total_results") == 1:
                    one_result.append({
                        "file_path": file_data['file_path'],
                        "season": season,
                        "episode": episode,
                        "data": data,
                        "extras": extras
                    })
                    print(f"One result found for {file_data['file_path']}: {data}")
                elif data.get("total_results") > 1:
                    multiple_results.append({
                        "file_path": file_data['file_path'],
                        "season": season,
                        "episode": episode,
                        "data": data,
                        "extras": extras
                    })
                    print(f"Multiple results found for {file_data['file_path']}: {data}")
                else:
                    print(f"No data found for {file_data['file_path']}.")
                    no_results.append(file_data)

            if file_type == "movie":
                if api_source == "omdb":
                    if data.get("Response") == "False":
                        print(f"No results found for {file_data['file_path']}: {data['Error']}")
                        no_results.append({
                            "file_path": file_data['file_path'],
                            "extras": extras
                        })
                    elif data.get("Response") == "True":
                        one_result.append({
                            "file_path": file_data['file_path'],
                            "data": data,
                            "extras": extras
                        })
                        print(f"One result found for {file_data['file_path']}: {data}")
                elif api_source == "tmdb":
                    if data.get("total_results") == 0:
                        print(f"No results found for {file_data['file_path']}: No results in TMDB response.")
                        no_results.append({
                            "file_path": file_data['file_path'],
                            "extras": extras
                        })
                    elif data.get("total_results") == 1:
                        one_result.append({
                            "file_path": file_data['file_path'],
                            "data": data,
                            "extras": extras
                        })
                        print(f"One result found for {file_data['file_path']}: {data}")
                    elif data.get("total_results") > 1:
                        multiple_results.append({
                            "file_path": file_data['file_path'],
                            "data": data,
                            "extras": extras
                        })
                        print(f"Multiple results found for {file_data['file_path']}: {data}")    

    return no_results, one_result, multiple_results
