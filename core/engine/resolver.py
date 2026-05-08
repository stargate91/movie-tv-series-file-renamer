"""
v3.1 Resolver: Orchestrates matching using MatchingEngine and LibraryManager.
"""

import os
import logging
import re
import concurrent.futures

from core.engine.matching_engine import MatchingEngine
from core.engine.library_manager import LibraryManager

logger = logging.getLogger(__name__)

class Resolver:
    """
    Orchestrator for the matching pipeline.
    Uses MatchingEngine for search logic and LibraryManager for data persistence.
    """

    def __init__(self, db, settings):
        self.db = db
        self.s = settings
        self.matcher = MatchingEngine(db, settings)
        self.library = LibraryManager(db, settings)

    def refresh_settings(self, settings):
        """Propagates new settings to children."""
        self.s = settings
        self.matcher.s = settings
        # Re-init API clients to pick up new keys
        from api.client import APIClient
        new_api = APIClient(
            omdb_key=settings.omdb_key,
            tmdb_key=settings.tmdb_key,
            tmdb_bearer_token=settings.tmdb_bearer_token,
            db=self.db
        )
        self.matcher.api = new_api
        self.library.refresh_settings(settings)

    def resolve_all(self, progress_callback=None):
        """Runs the full matching pipeline concurrently on all unmatched parent videos."""
        # Use FileRepository
        videos = self.db.files.get_files_by_category('video')
        # We process 'pending' files, but also 'matched' or 'multiple' 
        # to allow supplementing missing translations if the language changed.
        targets = []
        for v in videos:
            status = v['match_status']
            if status == 'pending' or status == 'multiple':
                targets.append(v)
            elif status == 'matched':
                # Only re-resolve if we need to supplement a new language
                target_lang = v.get('target_language') or self.s.metadata_language
                links = self.db.media.get_links_for_file(v['id'])
                if links:
                    media_item = self.db.media.get_media_item_by_id(links[0]['media_item_id'])
                    if media_item:
                        fetched = (media_item.get('fetched_languages') or "").split(',')
                        fetched = [l.strip() for l in fetched if l.strip()]
                        if target_lang not in fetched:
                            targets.append(v)
        
        
        completed = 0
        total = len(targets)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._resolve_single, vid): vid for vid in targets}
            
            for future in concurrent.futures.as_completed(futures):
                vid = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error resolving {vid['file_name']}: {e}")
                
                completed += 1
                if progress_callback:
                    if progress_callback(f"Resolved: {vid['file_name']}", completed, total) is False:
                        executor.shutdown(wait=False, cancel_futures=True)
                        return

    def resolve_file(self, file_id):
        """Public entry point to resolve a single file by ID."""
        # Use FileRepository
        vid = self.db.files.get_file_by_id(file_id)
        if vid:
            self._resolve_single(vid)

    def _resolve_single(self, vid):
        """Runs the refined deep waterfall for a single file."""
        file_id = vid['id']
        target_lang = vid.get('target_language') or self.s.metadata_language
        all_results = []
        seen_ids = set()

        def _add_results(results, source):
            nonlocal all_results, seen_ids
            for r in results:
                if r['tmdb_id'] not in seen_ids:
                    r['_source'] = source
                    all_results.append(r)
                    seen_ids.add(r['tmdb_id'])

        # ── Tier 1: NFO IMDB ID (Trusted) ──
        if vid['nfo_imdb_id']:
            result = self.matcher.resolve_by_imdb(vid['nfo_imdb_id'], language_override=target_lang)
            if result:
                media_item_id = self.library.store_result(result, language_override=target_lang)
                self._finalize_match(file_id, media_item_id, result, vid, 'matched', language_override=target_lang)
                return

        # ── Step A: Filename Analysis ──
        if vid['fn_title']:
            search_type = vid['fn_media_type'] or self.matcher.guess_search_type(vid)
            fn_results = self.matcher.search_api(vid['fn_title'], vid['fn_year'], search_type, language_override=target_lang)
            outcome, best_res = self._check_confidence(fn_results, vid['fn_title'], vid['fn_year'])
            if outcome == 'matched':
                media_item_id = self.library.store_result(best_res, language_override=target_lang)
                self._finalize_match(file_id, media_item_id, best_res, vid, 'matched', language_override=target_lang)
                return
            _add_results(fn_results, 'filename')

        # ── Step B: Folder Check ──
        if vid['fd_title']:
            search_type = vid['fd_media_type'] or self.matcher.guess_search_type(vid)
            fd_results = self.matcher.search_api(vid['fd_title'], vid['fd_year'], search_type, language_override=target_lang)
            outcome, best_res = self._check_confidence(fd_results, vid['fd_title'], vid['fd_year'])
            if outcome == 'matched':
                media_item_id = self.library.store_result(best_res, language_override=target_lang)
                self._finalize_match(file_id, media_item_id, best_res, vid, 'matched', language_override=target_lang)
                return
            _add_results(fd_results, 'foldername')

        # ── Step C: Internal Title Check ──
        it_year = None
        if vid['internal_title']:
            clean_fn = os.path.splitext(vid['file_name'])[0]
            if vid['internal_title'] != clean_fn and vid['internal_title'] != vid['file_name']:
                title, it_year = self.matcher.parse_with_guessit(vid['internal_title'])
                if title:
                    search_type = self.matcher.guess_search_type(vid)
                    it_results = self.matcher.search_api(title, it_year, search_type, language_override=target_lang)
                    outcome, best_res = self._check_confidence(it_results, title, it_year)
                    if outcome == 'matched':
                        media_item_id = self.library.store_result(best_res, language_override=target_lang)
                        self._finalize_match(file_id, media_item_id, best_res, vid, 'matched', language_override=target_lang)
                        return
                    _add_results(it_results, 'internal_title')

        # ── Final Fallback: Single Match, Multiple or No Match ──
        if len(all_results) == 1:
            best_res = all_results[0]
            media_item_id = self.library.store_result(best_res, language_override=target_lang)
            
            # Smart status: if year matches ANY of our detected years, it's high confidence
            res_year = str(best_res.get('year'))
            detected_years = [str(vid.get('fn_year') or ''), str(vid.get('fd_year') or ''), str(it_year or '')]
            
            status = 'matched' if (res_year and res_year in detected_years and res_year != '') else 'uncertain'
            
            self._finalize_match(file_id, media_item_id, best_res, vid, status, language_override=target_lang)
            return
        elif len(all_results) > 1:
            self._add_candidates_deduped(file_id, all_results, 'waterfall_merged', language_override=target_lang)
            self.db.files.update_file(file_id, match_status='multiple')
            return
        else:
            self.db.files.update_file(file_id, match_status='no_match')
            return

    def _check_confidence(self, results, search_title, search_year):
        """Helper to evaluate search results. Returns (outcome, best_result)."""
        if not results: return 'none', None

        # 1. Look for a single perfect match (Super Confident)
        super_confident = []
        year_matches = []
        
        for r in results:
            is_conf, is_super = self.matcher.confidence_check(r, search_title, search_year)
            if is_super:
                super_confident.append(r)
            
            # Check if year matches exactly (even if title is fuzzy)
            res_year = str(r.get('year') or '')
            if search_year and res_year == str(search_year):
                year_matches.append(r)

        if len(super_confident) == 1:
            return 'matched', super_confident[0]
        
        # 2. If we have multiple results, but only ONE matches the year exactly, pick it!
        if search_year and len(year_matches) == 1:
            return 'matched', year_matches[0]
            
        # 3. Fallback to general confidence
        confident = [r for r in results if self.matcher.confidence_check(r, search_title, search_year)[0]]
        if len(confident) == 1:
            return 'matched', confident[0]
        elif len(confident) > 1:
            return 'multiple', None
            
        return 'none', None

    def _evaluate_results(self, results, search_title, search_year, file_id, source, vid, language_override=None):
        """Evaluates search results with confidence check."""
        if not results: return 'none'

        confident = []
        super_confident = []
        
        for r in results:
            is_conf, is_super = self.matcher.confidence_check(r, search_title, search_year)
            if is_super:
                super_confident.append(r)
            elif is_conf:
                confident.append(r)

        # Priority 1: Super Confident (Exact title + Exact year)
        if len(super_confident) == 1:
            res = super_confident[0]
            media_item_id = self.library.store_result(res, language_override=language_override)
            self._finalize_match(file_id, media_item_id, res, vid, 'matched', language_override=language_override)
            return 'matched'
        
        # Priority 2: Only one confident match
        all_conf = super_confident + confident
        if len(all_conf) == 1:
            res = all_conf[0]
            media_item_id = self.library.store_result(res, language_override=language_override)
            self._finalize_match(file_id, media_item_id, res, vid, 'matched', language_override=language_override)
            return 'matched'
        elif len(all_conf) > 1:
            self._add_candidates_deduped(file_id, all_conf, source, language_override=language_override)
            return 'multiple'
            
        return 'none'

    def _finalize_match(self, file_id, media_item_id, res, vid, status='matched', language_override=None):
        """Links file to media and specific episodes and synchronizes file metadata."""
        # Ensure file metadata matches the resolved result (Movie vs TV)
        updates = {
            'match_status': status,
            'fn_media_type': res['media_type']
        }
        
        if res['media_type'] == 'tv':
            s_val = vid.get('fn_season') if vid.get('fn_season') is not None else vid.get('fd_season')
            try: season_num = int(s_val) if s_val is not None else None
            except (ValueError, TypeError): season_num = None
            
            if season_num is not None:
                updates['fn_season'] = season_num
                self.library.fetch_and_store_season(res['tmdb_id'], season_num, language_override=language_override)
                
                ep_val = vid.get('fn_episode') if vid.get('fn_episode') is not None else vid.get('fd_episode')
                ep_nums = self._parse_episode_numbers(ep_val)
                
                if ep_nums:
                    updates['fn_episode'] = str(ep_nums) if len(ep_nums) > 1 else str(ep_nums[0])
                    linked_any = False
                    for ep_num in ep_nums:
                        ep_row = self.db.media.get_episode_by_id_fields(media_item_id, int(season_num), int(ep_num))
                        if ep_row:
                            self.db.files.update_file(file_id, **updates)
                            self.db.media.link_file_to_media(file_id, media_item_id, tv_episode_id=ep_row['id'])
                            linked_any = True
                    
                    if not linked_any:
                        self.db.files.update_file(file_id, **updates)
                        self.db.media.link_file_to_media(file_id, media_item_id)
                else:
                    self.db.files.update_file(file_id, **updates)
                    self.db.media.link_file_to_media(file_id, media_item_id)
            else:
                self.db.files.update_file(file_id, **updates)
                self.db.media.link_file_to_media(file_id, media_item_id)
        else:
            self.db.files.update_file(file_id, **updates)
            self.db.media.link_file_to_media(file_id, media_item_id)

    def _parse_episode_numbers(self, ep_val):
        """Helper to extract episode numbers from various formats."""
        ep_nums = []
        if isinstance(ep_val, (list, tuple)):
            ep_nums = [int(n) for n in ep_val if str(n).isdigit()]
        elif ep_val is not None:
            if isinstance(ep_val, int):
                ep_nums = [ep_val]
            elif isinstance(ep_val, str):
                if ep_val.startswith('['):
                    import ast
                    try:
                        parsed = ast.literal_eval(ep_val)
                        ep_nums = [int(n) for n in (list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]) if str(n).isdigit()]
                    except: pass
                if not ep_nums:
                    try: ep_nums = [int(n) for n in re.findall(r'\d+', ep_val)]
                    except: pass
        return ep_nums

    def _add_candidates_deduped(self, file_id, results, source, language_override=None):
        """Adds candidates while avoiding duplicates."""
        # Use MatchRepository
        existing = self.db.matches.get_candidates(file_id)
        existing_ids = {c['tmdb_id'] for c in existing}
        
        for r in results:
            if r['tmdb_id'] not in existing_ids:
                self.library.store_result(r, language_override=language_override)
                # Use MatchRepository
                self.db.matches.add_candidate(file_id, r['tmdb_id'], r['title'], r['year'],
                                    r['media_type'], r.get('poster_path'), source)
                existing_ids.add(r['tmdb_id'])

    def resolve_from_local_data(self, file_id):
        """
        Triggered when manual metadata (Season/Ep) is updated.
        If the file already has a Series link, this tries to finalize the Episode link.
        """
        vid = self.db.files.get_file_by_id(file_id)
        if not vid: return
        
        links = self.db.media.get_links_for_file(file_id)
        if not links: return
        
        # We only auto-resolve if linked to a media item but NOT a specific episode yet
        # or if we want to RE-resolve due to number change.
        for link in links:
            mid = link['media_item_id']
            media = self.db.media.get_media_item_by_id(mid)
            if not media or media['media_type'] != 'tv': continue
            
            # Re-run finalization with current local data
            self._finalize_match(file_id, mid, media, vid, status='matched')
