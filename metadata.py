from parser import extract_extra_metadata
import os

def call_api_with_fallback(
    api_func,
    title_file,
    year_file,
    title_folder,
    year_folder,
    file,
    file_type="movie",
    source_mode="fallback"
):
    def has_result(result, min_count=1):
        return result and result.get("total_results", 0) >= min_count

    def result_count(result):
        return result.get("total_results", 0) if result else 0

    # --- Mode: Only file ---
    if source_mode == "file":
        result_file = api_func(title_file, year_file)
        return (result_file, "file") if has_result(result_file) else (None, "none")

    # --- Mode: Only folder ---
    if source_mode == "folder":
        result_folder = api_func(title_folder, year_folder)
        return (result_folder, "folder") if has_result(result_folder) else (None, "none")

    # --- Mode: Fallback ---
    result_file = api_func(title_file, year_file)
    count_file = result_count(result_file)

    if count_file == 1:
        return result_file, "file"

    elif count_file > 1:
        result_folder = api_func(title_folder, year_folder)
        count_folder = result_count(result_folder)

        if count_folder == 1:
            return result_folder, "folder"

        elif count_folder > 1:
            merged = (result_file.get("results", []) if result_file else []) + \
                     (result_folder.get("results", []) if result_folder else [])

            unique = {r["id"]: r for r in merged if "id" in r}
            if unique:
                return {
                    "page": 1,
                    "total_results": len(unique),
                    "results": list(unique.values())
                }, "mult"

        elif count_file > 0:
            return result_file, "file"

    else:
        result_folder = api_func(title_folder, year_folder)
        if has_result(result_folder):
            return result_folder, "folder"

    return None, "none"

def classify_result(api_data, file_info, collected_list):
    total = api_data.get("total_results", 0) if api_data else 0

    if total == 0:
        file_info['status'] = 'no_match'
        file_info['details'] = api_data
    elif total == 1:
        file_info['status'] = 'one_match'
        # Itt adjuk be közvetlenül a találatot, ne az egész választ
        file_info['details'] = api_data['results'][0] if api_data and 'results' in api_data else api_data
    else:
        file_info['status'] = 'multiple_matches'
        file_info['details'] = api_data

    collected_list.append(file_info)


def extract_metadata(video_files, api_client, source_mode):
    if not video_files:
        print("[INFO] No valid video files, please select another folder. Exiting now.")
        return [], []

    collected_list = []
    unknown_files = []

    for file in video_files:
        file_name = os.path.basename(file)
        folder_name = os.path.basename(os.path.dirname(file))

        result = extract_extra_metadata(file, unknown_files, file_name, folder_name)
        if result is None:
            continue

        file_result, folder_result, file_type, merged_extras = result

        file_info = {
            'file_path': file,
            'file_type': file_type,
            'extras': merged_extras
        }

        if file_type == "movie":
            m_title_file = file_result.get('title', 'unknown')
            m_year_file = file_result.get('year', 'unknown')
            m_title_folder = folder_result.get('title', 'unknown')
            m_year_folder = folder_result.get('year', 'unknown')

            api_func = api_client.get_from_tmdb_movie
            api_data, _ = call_api_with_fallback(api_func, m_title_file, m_year_file, m_title_folder, m_year_folder, file, file_type, source_mode)

            classify_result(api_data, file_info, collected_list)

        elif file_type == "episode":
            e_title_file = file_result.get('title', 'unknown')
            e_year_file = file_result.get('year', 'unknown')
            season_file = file_result.get('season', 'unknown')
            episode_file = file_result.get('episode', 'unknown')

            e_title_folder = folder_result.get('title', 'unknown')
            e_year_folder = folder_result.get('year', 'unknown')
            season_folder = folder_result.get('season', 'unknown')
            episode_folder = folder_result.get('episode', 'unknown')

            file_info.update({
                'season_file': season_file,
                'episode_file': episode_file,
                'season_folder': season_folder,
                'episode_folder': episode_folder
            })

            api_func = api_client.get_from_tmdb_tv
            api_data, _ = call_api_with_fallback(api_func, e_title_file, e_year_file, e_title_folder, e_year_folder, file, file_type, source_mode)

            classify_result(api_data, file_info, collected_list)

    return collected_list, unknown_files
