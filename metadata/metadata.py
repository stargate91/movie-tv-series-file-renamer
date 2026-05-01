from metadata.parser import extract_extra_metadata
import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.cache import FileMatchCache
from metadata.video_metadata import get_video_metadata

logger = logging.getLogger(__name__)
FILE_CACHE = FileMatchCache()

def call_api_with_fallback(
    api_func,
    title_file,
    year_file,
    title_folder,
    year_folder,
    file,
    file_type="movie",
    source_mode="fallback",
    language="hu-HU"
):
    def has_result(result, min_count=1):
        return result and result.get("total_results", 0) >= min_count

    def result_count(result):
        return result.get("total_results", 0) if result else 0

    # --- Mode: Only file ---
    if source_mode == "file":
        result_file = api_func(title_file, year_file, language=language)
        return (result_file, "file") if has_result(result_file) else (None, "none")

    # --- Mode: Only folder ---
    if source_mode == "folder":
        result_folder = api_func(title_folder, year_folder, language=language)
        return (result_folder, "folder") if has_result(result_folder) else (None, "none")

    # --- Mode: Fallback (Bulletproof Logic v2) ---
    search_file = title_file not in [None, 'unknown', '']
    search_folder = title_folder not in [None, 'unknown', '']

    # 1. Check File
    res_file = api_func(title_file, year_file, language=language) if search_file else None
    count_file = result_count(res_file)

    if count_file == 1:
        return res_file, "file"

    # 2. Check Folder
    res_folder = api_func(title_folder, year_folder, language=language) if search_folder else None
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
                    ep_data = api_client.get_from_tmdb_episode(tv_id, season, episode)
                    if ep_data and 'id' in ep_data:
                        # Enrich with series context
                        ep_data['series_poster_path'] = series_data.get('poster_path')
                        ep_data['series_name'] = series_data.get('name') or series_data.get('title')
                        ep_data['series_id'] = tv_id # Store the actual series ID
                        
                        # Fetch season details for dates and season poster
                        season_data = api_client.get_from_tmdb_season(tv_id, season)
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

    # Save to file-level cache if it's a definitive match
    if file_info['status'] in ('one_match', 'complex_match'):
        FILE_CACHE.set_match(file_info['file_path'], file_info)

    collected_list.append(file_info)


def extract_metadata(video_files, api_client, source_mode, ui=None, language="hu-HU", discovery_data=None):
    if not video_files:
        logger.info("No valid video files, please select another folder.")
        return [], []

    collected_list = []
    unknown_files = []
    total = len(video_files)
    processed_count = 0
    progress_lock = threading.Lock()
    discovery_data = discovery_data or {}

    def process_single_file(file):
        nonlocal processed_count
        
        # 1. Check File Match Cache
        cached_info = FILE_CACHE.get_match(file)
        if cached_info:
            # Cache-busting: If we have a part in filename but not in cache, re-process
            import guessit
            g = guessit.guessit(os.path.basename(file))
            if (g.get('part') or g.get('cd')) and not cached_info.get('part'):
                logger.info(f"Cache miss (missing part info) for {file}, re-analyzing...")
                pass # Continue to re-processing
            else:
                with progress_lock:
                    processed_count += 1
                    if ui: ui.update_progress(processed_count, total, f"Status: Metadata cached {processed_count}/{total}")
                return cached_info, None

        # Initialize result entry
        meta = {
            'file_path': file,
            'file_type': 'unknown',
            'status': 'no_match',
            'details': None,
            'extras': {},
            'is_manual': False,
            'discovery': discovery_data.get(file, {})
        }
        
        # Get Technical Metadata (MediaInfo)
        tech_extras = get_video_metadata(file)
        
        # Get Parsed Metadata (Guessit)
        file_name = os.path.basename(file)
        folder_name = os.path.basename(os.path.dirname(file))
        from metadata.parser import extract_extra_metadata
        parsed = extract_extra_metadata(file, [], file_name, folder_name)
        
        if parsed:
            file_res, folder_res, file_type, merged_extras = parsed
            meta['extras'] = {**tech_extras, **merged_extras}
            meta['file_type'] = file_type
            # Store parsed title/year for search
            meta['parsed_title_file'] = file_res.get('title')
            meta['parsed_year_file'] = file_res.get('year')
            meta['parsed_title_folder'] = folder_res.get('title')
            meta['parsed_year_folder'] = folder_res.get('year')
            
            # Store episode info
            meta['season_file'] = file_res.get('season', 'unknown')
            meta['episode_file'] = file_res.get('episode', 'unknown')
            meta['season_folder'] = folder_res.get('season', 'unknown')
            meta['episode_folder'] = folder_res.get('episode', 'unknown')
            
            # Store part/cd info
            part_val = merged_extras.get('part') or merged_extras.get('cd')
            meta['part'] = f"CD{part_val}" if part_val else ""
        else:
            meta['extras'] = tech_extras
            meta['file_type'] = tech_extras.get('type', 'movie')
        
        # 2. PRIORITY: Discovery Data (NFO IDs)
        disc = meta['discovery']
        tmdb_id = disc.get('tmdb_id')
        imdb_id = disc.get('imdb_id')
        
        # Merge discovery part if filename parsing missed it
        if disc.get('part') and not meta.get('part'):
            meta['part'] = disc['part']
        
        raw_result = None
        
        if tmdb_id:
            logger.info(f"Using discovered TMDB ID: {tmdb_id}")
            if meta['file_type'] == 'episode':
                raw_result = api_client.get_tv_show_details(tmdb_id, language=language)
            else:
                raw_result = api_client.get_movie_details(tmdb_id, language=language)
            if raw_result:
                raw_result = {'results': [raw_result], 'total_results': 1}
        
        elif imdb_id:
            logger.info(f"Using discovered IMDB ID: {imdb_id}")
            raw_result = api_client.get_by_external_id(imdb_id, language=language)
            if raw_result:
                movie_res = raw_result.get('movie_results', [])
                tv_res = raw_result.get('tv_results', [])
                all_res = movie_res + tv_res
                if all_res:
                    raw_result = {'results': all_res, 'total_results': len(all_res)}
                else:
                    raw_result = None

        # 3. SECONDARY: Internal Title Search
        if not raw_result and disc.get('internal_title'):
            search_query = disc['internal_title']
            logger.info(f"Using discovered internal title: {search_query}")
            if meta['file_type'] == 'episode':
                raw_result = api_client.search_tv(search_query, language=language)
            else:
                raw_result = api_client.search_movie(search_query, language=language)

        # 4. FALLBACK: Normal Search by filename
        if not raw_result:
            file_name = os.path.basename(file)
            folder_name = os.path.basename(os.path.dirname(file))
            
            from metadata.metadata import call_api_with_fallback
            api_func = api_client.search_tv if meta['file_type'] == 'episode' else api_client.search_movie
            
            raw_result, source = call_api_with_fallback(
                api_func,
                meta.get('parsed_title_file'),
                meta.get('parsed_year_file'),
                meta.get('parsed_title_folder'),
                meta.get('parsed_year_folder'),
                file,
                file_type=meta['file_type'],
                source_mode=source_mode,
                language=language
            )
        
        # Classify findings
        temp_list = []
        if raw_result:
            classify_result(raw_result, meta, temp_list, api_client)
        else:
            meta['status'] = 'no_match'
            temp_list.append(meta)
            
        with progress_lock:
            processed_count += 1
            if ui: ui.update_progress(processed_count, total, f"Status: Analyzing {processed_count}/{total}")
            
        return temp_list[0], (file if meta['status'] == 'no_match' else None)

    # Execute in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_file, f) for f in video_files]
        for future in as_completed(futures):
            f_info, u_file = future.result()
            if f_info:
                collected_list.append(f_info)
            if u_file:
                unknown_files.append(u_file)

    return collected_list, unknown_files
