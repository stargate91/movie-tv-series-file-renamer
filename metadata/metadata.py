from metadata.parser import extract_extra_metadata
import os
import logging

logger = logging.getLogger(__name__)

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

    # --- Mode: Fallback (Bulletproof Logic v2) ---
    search_file = title_file not in [None, 'unknown', '']
    search_folder = title_folder not in [None, 'unknown', '']

    # 1. Check File
    res_file = api_func(title_file, year_file) if search_file else None
    count_file = result_count(res_file)

    if count_file == 1:
        return res_file, "file"

    # 2. Check Folder
    res_folder = api_func(title_folder, year_folder) if search_folder else None
    count_folder = result_count(res_folder)

    # 3. Decision
    if count_folder == 1:
        return res_folder, "folder"
    
    if count_folder == 0:
        # If folder fails, return file's multi-match if it exists, otherwise no-match
        if count_file > 1:
            return res_file, "file"
        return None, "none"

    # 4. If folder is Multiple
    if count_folder > 1:
        if count_file > 1:
            # Both are Multiple -> Merge
            merged_results = (res_file.get("results", []) if res_file else []) + \
                             (res_folder.get("results", []) if res_folder else [])
            unique = {r["id"]: r for r in merged_results if "id" in r}
            return {
                "page": 1,
                "total_results": len(unique),
                "results": list(unique.values())
            }, "mult"
        else:
            # Only folder is Multiple (file was 0)
            return res_folder, "folder"

    return None, "none"

def classify_result(api_data, file_info, collected_list, api_client=None):
    total = api_data.get("total_results", 0) if api_data else 0

    if total == 0:
        file_info['status'] = 'no_match'
        file_info['details'] = api_data
    elif total == 1:
        file_info['status'] = 'one_match'
        series_data = api_data['results'][0] if api_data and 'results' in api_data else api_data
        file_info['details'] = series_data
        
        # If it's an episode, try to fetch specific episode details
        if file_info['file_type'] == 'episode' and api_client:
            tv_id = series_data.get('id')
            season = file_info.get('season_file') if file_info.get('season_file') != 'unknown' else file_info.get('season_folder')
            episode = file_info.get('episode_file') if file_info.get('episode_file') != 'unknown' else file_info.get('episode_folder')
            
            # If it's a multi-episode file (list), we force it to Needs Attention
            if isinstance(season, list) or isinstance(episode, list):
                file_info['status'] = 'complex_match'
            
            if tv_id and season != 'unknown' and episode != 'unknown' and not isinstance(season, list) and not isinstance(episode, list):
                try:
                    ep_data = api_client.get_tv_episode_details(tv_id, season, episode)
                    if ep_data and 'id' in ep_data:
                        # Enrich with series context
                        ep_data['series_poster_path'] = series_data.get('poster_path')
                        ep_data['series_name'] = series_data.get('name') or series_data.get('title')
                        
                        # Fetch season details for dates and season poster
                        season_data = api_client.get_tv_season_details(tv_id, season)
                        if season_data:
                            ep_data['season_poster_path'] = season_data.get('poster_path')
                            ep_data['season_air_date'] = season_data.get('air_date', '')
                            # Get year range for season if possible
                            s_year = season_data.get('air_date', '')[:4]
                            ep_data['season_year_range'] = f"({s_year})" if s_year else ""
                        
                        file_info['details'] = ep_data
                except Exception as e:
                    logger.error(f"Failed to fetch episode/season details: {e}")
                    file_info['status'] = 'multiple_matches'

    else:
        file_info['status'] = 'multiple_matches'
        file_info['details'] = api_data

    collected_list.append(file_info)


def extract_metadata(video_files, api_client, source_mode, ui=None):
    if not video_files:
        logger.info("No valid video files, please select another folder.")
        return [], []

    collected_list = []
    unknown_files = []

    total = len(video_files)
    for idx, file in enumerate(video_files, 1):
        if ui:
            ui.update_progress(idx, total, f"Status: Fetching metadata {idx}/{total}")
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
            classify_result(api_data, file_info, collected_list, api_client)

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
            classify_result(api_data, file_info, collected_list, api_client)

    return collected_list, unknown_files
