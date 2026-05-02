import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from metadata.discovery import MetadataDiscovery
from metadata.classifier import classify_result, FILE_CACHE
from metadata.parser import extract_extra_metadata
from metadata.video_metadata import get_video_metadata
from metadata.metadata_standardizer import standardize_metadata
from metadata.metadata_enricher import enricher
from core.models import Movie, Episode

logger = logging.getLogger(__name__)

class MetadataManager:
    """
    Handles metadata discovery (NFO), extraction (API Search), and enrichment.
    """
    def __init__(self, api_client, settings, ui=None):
        self.api = api_client
        self.s = settings
        self.ui = ui

    def discover(self, video_files):
        """Analyzes files for NFOs and internal metadata."""
        discovery = MetadataDiscovery()
        return discovery.discover(video_files, ui=self.ui)

    def extract(self, video_files, discovery_data):
        """
        Parses filenames and queries APIs for initial matches.
        Replaces the legacy extract_metadata from metadata.py.
        """
        if not video_files:
            return [], []

        collected_list = []
        unknown_files = []
        total = len(video_files)
        processed_count = 0
        progress_lock = threading.Lock()
        discovery_data = discovery_data or {}
        lang = self.s.metadata_language

        def process_single_file(file):
            nonlocal processed_count
            
            # 1. Check File Match Cache
            cached_info = FILE_CACHE.get_match(file)
            if cached_info:
                from guessit import guessit
                g = guessit(os.path.basename(file))
                if (g.get('part') or g.get('cd')) and not cached_info.get('part'):
                    pass # Force re-analysis if part info is missing in cache
                else:
                    with progress_lock:
                        processed_count += 1
                        if self.ui: self.ui.update_progress(processed_count, total, f"Status: Metadata cached {processed_count}/{total}")
                    return cached_info, None

            # Initialize result entry
            meta = {
                'file_path': file,
                'file_type': 'unknown',
                'status': 'no_match',
                'details': None,
                'extras': {},
                'is_manual': False,
                'discovery': discovery_data.get(file, {}),
                'match_source': 'none'
            }
            
            if not file:
                return None, None

            tech_extras = get_video_metadata(file)
            file_name = os.path.basename(file)
            folder_path = os.path.dirname(file)
            folder_name = os.path.basename(folder_path) if folder_path else ""
            parsed = extract_extra_metadata(file, [], file_name, folder_name)
            
            if parsed:
                file_res, folder_res, file_type, merged_extras = parsed
                meta['extras'] = {**tech_extras, **merged_extras}
                meta['file_type'] = file_type
                meta['parsed_title_file'] = file_res.get('title')
                meta['parsed_year_file'] = file_res.get('year')
                meta['parsed_title_folder'] = folder_res.get('title')
                meta['parsed_year_folder'] = folder_res.get('year')
                meta['season_file'] = file_res.get('season', 'unknown')
                meta['episode_file'] = file_res.get('episode', 'unknown')
                meta['season_folder'] = folder_res.get('season', 'unknown')
                meta['episode_folder'] = folder_res.get('episode', 'unknown')
                part_val = merged_extras.get('part') or merged_extras.get('cd')
                meta['part'] = f"CD{part_val}" if part_val else ""
            else:
                meta['extras'] = tech_extras
                meta['file_type'] = tech_extras.get('type', 'movie')
            
            disc = meta['discovery']
            if disc.get('part') and not meta.get('part'):
                meta['part'] = disc['part']

            # --- HIERARCHICAL MATCHING ENGINE ---
            raw_result = None
            match_source = 'none'

            # 1. TIER: NFO IDs (Definitive)
            tmdb_id = disc.get('tmdb_id')
            imdb_id = disc.get('imdb_id')
            nfo_type = disc.get('nfo_type') # movie or episode
            
            if tmdb_id or imdb_id:
                # Use external ID lookup which is type-agnostic
                target_id = tmdb_id or imdb_id
                id_res = self.api.get_by_external_id(target_id, language=lang)
                
                if id_res:
                    # Check both buckets
                    movie_res = id_res.get('movie_results', [])
                    tv_res = id_res.get('tv_results', [])
                    
                    if movie_res:
                        raw_result = {'results': [movie_res[0]], 'total_results': 1}
                        meta['file_type'] = 'movie' # Force correct type
                        match_source = 'nfo_id'
                    elif tv_res:
                        raw_result = {'results': [tv_res[0]], 'total_results': 1}
                        meta['file_type'] = 'episode' # Force correct type
                        match_source = 'nfo_id'
            
            # 2. TIER: Internal Title (FFmpeg/MediaInfo)
            if (not raw_result or raw_result.get('total_results', 0) != 1) and disc.get('internal_title'):
                it_func = self.api.search_tv if meta['file_type'] == 'episode' else self.api.search_movie
                year_hint = meta.get('parsed_year_file') or meta.get('parsed_year_folder')
                it_result = it_func(disc['internal_title'], year_hint, language=lang)
                if it_result and it_result.get('total_results', 0) == 1:
                    raw_result = it_result
                    match_source = 'internal_title'

            # 3. TIER: Filename Search (GuessIt)
            if not raw_result or raw_result.get('total_results', 0) == 0:
                api_func = self.api.search_tv if meta['file_type'] == 'episode' else self.api.search_movie
                title_f = meta.get('parsed_title_file')
                year_f = meta.get('parsed_year_file')
                if title_f:
                    res_f = api_func(title_f, year_f, language=lang)
                    count_f = res_f.get('total_results', 0) if res_f else 0
                    
                    if count_f == 1:
                        raw_result = res_f
                        match_source = 'guessit_file'
                    elif count_f > 1:
                        # MULTI: Try Folder Fallback and MERGE results
                        title_fold = meta.get('parsed_title_folder')
                        year_fold = meta.get('parsed_year_folder')
                        if title_fold:
                            res_fold = api_func(title_fold, year_fold, language=lang)
                            count_fold = res_fold.get('total_results', 0) if res_fold else 0
                            if count_fold == 1:
                                raw_result = res_fold
                                match_source = 'guessit_folder'
                            elif count_fold > 1:
                                # Both are MULTI -> MERGE them
                                combined = res_f.get('results', []) + res_fold.get('results', [])
                                # Unique by ID
                                unique = {r['id']: r for r in combined if 'id' in r}
                                raw_result = {'results': list(unique.values()), 'total_results': len(unique)}
                                match_source = 'guessit_multi_merged'
                            else:
                                # Folder is No Match -> Keep Filename Multi
                                raw_result = res_f
                                match_source = 'guessit_multi'
                        else:
                            raw_result = res_f
                            match_source = 'guessit_multi'
                    else:
                        # NO MATCH on filename -> Try Folder Fallback
                        title_fold = meta.get('parsed_title_folder')
                        year_fold = meta.get('parsed_year_folder')
                        if title_fold:
                            res_fold = api_func(title_fold, year_fold, language=lang)
                            if res_fold and res_fold.get('total_results', 0) > 0:
                                raw_result = res_fold
                                match_source = 'guessit_folder'
            
            # --- FINAL SANITY CHECK & OVERRIDES ---
            if raw_result and raw_result.get('total_results', 0) == 1:
                # If NFO was definitive but GuessIt found S/E, we trust NFO Type
                if match_source == 'nfo_id' and nfo_type:
                    meta['file_type'] = nfo_type
                    if nfo_type == 'movie':
                        # Clear episode data if NFO says it's a movie
                        meta['season_file'] = 'unknown'
                        meta['episode_file'] = 'unknown'
            
            meta['match_source'] = match_source
            
            temp_list = []
            if raw_result:
                classify_result(raw_result, meta, temp_list, self.api)
            else:
                meta['status'] = 'no_match'
                temp_list.append(meta)
                
            with progress_lock:
                processed_count += 1
                source_label = meta.get('match_source', 'none')
                if self.ui: self.ui.update_progress(processed_count, total, f"Status: Analyzing {processed_count}/{total} ({source_label})")
                
            return temp_list[0], (file if meta['status'] == 'no_match' else None)

        try:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(process_single_file, f) for f in video_files]
                for future in as_completed(futures):
                    try:
                        f_info, u_file = future.result()
                        if f_info:
                            collected_list.append(f_info)
                        if u_file:
                            unknown_files.append(u_file)
                    except Exception as e:
                        if "API Authentication failed" in str(e):
                            raise e # Re-raise to be caught by the outer try-block
                        logger.error(f"Error processing file: {e}")
        except Exception as e:
            if self.ui:
                self.ui.update_progress(0, 100, f"CRITICAL ERROR: {str(e)}")
            raise e # Pass it up to TaskCoordinator

        return collected_list, unknown_files

    def standardize_and_enrich(self, handled_results, discovery_data, metadata_map, current_enriched):
        """Converts dicts to Models, fetches extra details and markings."""
        standardized, missing = standardize_metadata(handled_results)
        
        if not any([standardized, missing]):
            return current_enriched, []

        new_enriched, unexpected = enricher(
            standardized, self.api, self.ui, 
            language=self.s.metadata_language,
            fallback_language=self.s.fallback_language,
            templates=[self.s.movie_template, self.s.episode_template],
            discovery_data=discovery_data
        )
        
        enriched_map = {}
        for f in current_enriched:
            if f and hasattr(f, 'file_path') and f.file_path:
                norm_p = os.path.abspath(os.path.normpath(f.file_path))
                enriched_map[norm_p] = f
        
        for item in new_enriched:
            if item and hasattr(item, 'file_path') and item.file_path:
                norm_p = os.path.abspath(os.path.normpath(item.file_path))
                enriched_map[norm_p] = item
            
            cached_data = {
                'file_path': item.file_path,
                'file_type': item.file_type,
                'status': 'one_match',
                'details': item.__dict__,
                'is_manual': metadata_map.get(norm_p, {}).get('is_manual', False),
                'is_enriched': True
            }
            metadata_map[norm_p] = cached_data
            FILE_CACHE.set_match(item.file_path, cached_data)
        
        if self.ui:
            self.ui.update_progress(100, 100, "Status: Data Ready")
            
        return list(enriched_map.values()), unexpected

    def hydrate_from_cache(self, cached_results):
        hydrated = []
        for res in cached_results:
            if not isinstance(res, dict) or res.get('status') != 'one_match':
                continue
                
            f_type = res.get('file_type')
            details = res.get('details', {})
            if f_type == 'movie':
                model = Movie.from_dict(details)
            else:
                model = Episode.from_dict(details)
            if model:
                hydrated.append(model)
        return hydrated
