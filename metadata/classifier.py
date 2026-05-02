import os
import logging
from utils.cache import FileMatchCache

logger = logging.getLogger(__name__)
FILE_CACHE = FileMatchCache()

EXTRA_TYPE_MAP = {
    'sample': 'Sample / Clip',
    'trailer': 'Trailer',
    'deleted scene': 'Deleted Scene',
    'behind the scenes': 'Behind the Scenes',
    'featurette': 'Featurette / Short',
    'interview': 'Interview',
    'other': 'Other Extra'
}

def batch_classify(video_files, min_size_mb):
    """
    Stupid Simple classification of video files into 'movie/episode' or 'extra'.
    Returns a dict: { path: (category, extra_type, parent_name) }
    """
    results = {}
    for path in video_files:
        if not path: continue
        category = 'movie' # Default
        extra_type = None
        parent_name = None
        
        file_name = os.path.basename(path).lower()
        folder_path = os.path.dirname(path)
        dir_name = os.path.basename(folder_path).lower() if folder_path else ""
        rel_path = path.lower()
        
        # 1. Size-based classification (Samples)
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            if size_mb < min_size_mb:
                category = 'extra'
                extra_type = 'sample'
        except:
            pass
            
        # 2. Path-based classification (Keywords)
        extra_keywords = ['extra', 'featurette', 'behind the scenes', 'deleted scene', 'interview', 'trailer']
        if any(kw in rel_path for kw in extra_keywords) or 'sample' in file_name:
            category = 'extra'
            if not extra_type:
                for kw in extra_keywords:
                    if kw in rel_path:
                        extra_type = kw
                        break
                if 'sample' in file_name:
                    extra_type = 'sample'

        # 4. Same-folder and Parent-folder detection (Recursive)
        if category == 'extra' and not parent_name:
            current_lookup_dir = folder_path
            # Search up to 2 levels up for a parent
            for _ in range(3):
                norm_folder = os.path.normpath(current_lookup_dir).lower()
                folder_files = [f for f in video_files if os.path.normpath(os.path.dirname(f)).lower() == norm_folder and f != path]
                
                if folder_files:
                    # Sort by size to pick the largest file as parent
                    try:
                        folder_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
                    except: pass
                    
                    # Try name matching first
                    base_no_ext = os.path.splitext(file_name)[0].lower()
                    target = base_no_ext.replace('sample', '').replace('trailer', '').strip(' -._')
                    
                    found = False
                    for f in folder_files:
                        f_base = os.path.basename(f).lower()
                        if target and (target in f_base or f_base.replace(os.path.splitext(f_base)[1], '') in base_no_ext):
                            parent_name = os.path.basename(f)
                            found = True
                            break
                    
                    if not found and folder_files:
                        # Fallback to largest file in this folder
                        parent_name = os.path.basename(folder_files[0])
                        found = True
                    
                    if found:
                        break
                
                # Move up one level
                new_dir = os.path.dirname(current_lookup_dir)
                if new_dir == current_lookup_dir or not new_dir:
                    break
                current_lookup_dir = new_dir

        results[path] = (category, extra_type, parent_name)
        
    return results

def classify_result(api_data, file_info, collected_list, api_client=None):
    """
    Classifies the API search result and enriches file_info with details.
    Handles single matches, multi-matches, and no-matches.
    """
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
                        ep_data['series_id'] = tv_id
                        
                        # Fetch season details
                        season_data = api_client.get_from_tmdb_season(tv_id, season)
                        if season_data:
                            ep_data['season_poster_path'] = season_data.get('poster_path')
                            ep_data['season_air_date'] = season_data.get('air_date', '')
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
