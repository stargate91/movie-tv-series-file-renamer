import os
from guessit import guessit

def call_api_with_fallback(
    api_func, 
    title_file,
    year_file,
    title_folder,
    year_folder,
    file,
    api_source="tmdb",
    file_type="movie",
    source_mode="fallback"
):
    if api_source == "omdb" and file_type == "episode":
        print(f"[WARNING] OMDb cannot handle TV episodes: {file}")
        return None, "none"
    if api_source == "omdb":
        
        if source_mode == "file":
            result_file = api_func(title_file, year_file)
            if result_file and result_file.get("Response") == "True":
                return result_file, "file"

            return None, "none"

        if source_mode == "folder":
            result_folder = api_func(title_folder, year_folder)
            if result_folder and result_folder.get("Response") == "True":
                return result_folder, "folder"

            return None, "none"

        if source_mode == "fallback":
            result_file = api_func(title_file, year_file)

            if result_file and result_file.get("Response") == "True":
                return result_file, "file"

            result_folder = api_func(title_folder, year_folder)

            if result_folder and result_folder.get("Response") == "True":
                return result_folder, "folder"

            return None, "none"

    elif api_source == "tmdb":
        if source_mode == "file":
            result_file = api_func(title_file, year_file)

            if result_file and result_file.get("total_results", 0) >= 1:
                return result_file, "file"

            return None, "none"

        if source_mode == "folder":
            result_folder = api_func(title_folder, year_folder)
            if result_folder and result_folder.get("total_results", 0) >= 1:
                return result_folder, "folder"

        if source_mode == "fallback":
            result_file = api_func(title_file, year_file)

            if result_file and result_file.get("total_results", 0) == 1:
                return result_file, "file"

            elif result_file and result_file.get("total_results", 0) > 1:
                result_folder = api_func(title_folder, year_folder)

                if result_folder and result_folder.get("total_results", 0) == 1:
                    return result_folder, "folder"

                elif result_folder and result_folder.get("total_results", 0) > 1:

                    merged_results = result_file.get("results", []) + result_folder.get("results", [])
                    unique_results = {r["id"]: r for r in merged_results if "id" in r}

                    merged_result_obj = {
                        "page": 1,
                        "total_results": len(unique_results),
                        "results": list(unique_results.values())
                    }

                    return merged_result_obj, "mult"

                return result_file, "file"

            result_folder = api_func(title_folder, year_folder)
            if result_folder and result_folder.get("total_results", 0) > 0:
                return result_folder, "folder"

            return None, "none"

def classify_result(api_data, file_info, lists, file_type, api_source):
    if api_data is None:
        lists['no'].append(file_info)
    else:
        if api_source == "omdb":
            if api_data.get("Response") == "True":
                lists['one'].append({**file_info, 'details': api_data})
            else:
                lists['no'].append(file_info)
        else: 
            mult_results = (file_type == "movie" and api_data.get("total_results", 1) > 1) or \
                           (file_type == "episode" and api_data.get("total_results", 1) > 1)
            if mult_results:
                lists['mult'].append({**file_info, 'details': api_data})
            else:
                lists['one'].append({**file_info, 'details': api_data})

def extract_metadata(video_files, api_client, api_source, source_mode):
    if not video_files:
        print("[INFO] No valid video files, please select another folder. Exiting now.")
        return [], [], [], [], [], [], []

    movie_lists = {'one': [], 'no': [], 'mult': []}
    episode_lists = {'one': [], 'no': [], 'mult': []}
    unknown_files = []

    for file in video_files:
        file_name = os.path.basename(file)
        folder_name = os.path.basename(os.path.dirname(file))

        file_result = guessit(file_name)
        folder_result = guessit(folder_name)

        file_type = file_result.get('type', 'unknown')

        if file_type not in ["movie", "episode"]:
            print(f"[WARNING] Unknown file type for {file}: {file_type}")
            unknown_files.append(file)
            continue

        extras_keys = ['title', 'year', 'season', 'episode', 'type', 'screen_size', 'video_codec', 'audio_codec', 'audio_channels', 'language']
        file_extras = {k: v for k, v in file_result.items() if k not in extras_keys}
        folder_extras = {k: v for k, v in folder_result.items() if k not in extras_keys}
        merged_extras = folder_extras.copy()
        merged_extras.update(file_extras)

        print(f"\nExtra metadata extracted from file and folder names for:\n   {file}")
        print("These will be included in the final metadata:")
        for k, v in merged_extras.items():
                print(f"   • {k.ljust(16)}: {v}")

        if file_type == "movie":
            m_title_file = file_result.get('title', 'unknown')
            m_year_file = file_result.get('year', 'unknown')
            m_title_folder = folder_result.get('title', 'unknown')
            m_year_folder = folder_result.get('year', 'unknown')

            if api_source == "omdb":
                api_func = api_client.get_from_omdb
            else:
                api_func = api_client.get_from_tmdb_movie

            api_data, _ = call_api_with_fallback(api_func, m_title_file, m_year_file, m_title_folder, m_year_folder, file, api_source, file_type)
            file_info = {
                'file_path': file,
                'file_type': file_type,
                'extras': merged_extras
            }
            classify_result(api_data, file_info, movie_lists, file_type, api_source)

        elif file_type == "episode":
            e_title_file = file_result.get('title', 'unknown')
            e_year_file = file_result.get('year', 'unknown')
            season_file = file_result.get('season', 'unknown')
            episode_file = file_result.get('episode', 'unknown')

            e_title_folder = folder_result.get('title', 'unknown')
            e_year_folder = folder_result.get('year', 'unknown')
            season_folder = folder_result.get('season', 'unknown')
            episode_folder = folder_result.get('episode', 'unknown')

            api_func = api_client.get_from_tmdb_tv
            api_data, _ = call_api_with_fallback(api_func, e_title_file, e_year_file, e_title_folder, e_year_folder, file, "tmdb")
            file_info = {
                'file_path': file,
                'file_type': file_type,
                'season_file': season_file,
                'episode_file': episode_file,
                'season_folder': season_folder,
                'episode_folder': episode_folder,
                'extras': merged_extras
            }
            classify_result(api_data, file_info, episode_lists, file_type, "tmdb")

    return [
    movie_lists['one'],
    movie_lists['no'],
    movie_lists['mult'],
    episode_lists['one'],
    episode_lists['no'],
    episode_lists['mult'],
    unknown_files
    ]