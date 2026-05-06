"""
v3.1 Resolver: Orchestrates matching using MatchingEngine and LibraryManager.
"""

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
        """Runs the waterfall for a single file."""
        file_id = vid['id']
        target_lang = vid.get('target_language') # Per-file override

        # ── Tier 1: NFO IMDB ID (trusted) ──
        if vid['nfo_imdb_id']:
            result = self.matcher.resolve_by_imdb(vid['nfo_imdb_id'], language_override=target_lang)
            if result:
                media_item_id = self.library.store_result(result, language_override=target_lang)
                self._finalize_match(file_id, media_item_id, result, vid, 'matched', language_override=target_lang)
                return

        # ── Tier 2: FFmpeg internal title ──
        if vid['internal_title']:
            title, year = self.matcher.parse_title_year(vid['internal_title'])
            if title:
                search_type = self.matcher.guess_search_type(vid)
                results = self.matcher.search_api(title, year, search_type, language_override=target_lang)
                outcome = self._evaluate_results(results, title, year, file_id, 'internal_title', vid, language_override=target_lang)
                if outcome == 'matched': return

        # ── Tier 3: Filename GuessIt ──
        if vid['fn_title']:
            search_type = vid['fn_media_type'] or self.matcher.guess_search_type(vid)
            results = self.matcher.search_api(vid['fn_title'], vid['fn_year'], search_type, language_override=target_lang)
            outcome = self._evaluate_results(results, vid['fn_title'], vid['fn_year'], file_id, 'filename', vid, language_override=target_lang)
            if outcome == 'matched': return

        # ── Tier 4: Foldername GuessIt ──
        if vid['fd_title']:
            search_type = vid['fd_media_type'] or self.matcher.guess_search_type(vid)
            results = self.matcher.search_api(vid['fd_title'], vid['fd_year'], search_type, language_override=target_lang)
            outcome = self._evaluate_results(results, vid['fd_title'], vid['fd_year'], file_id, 'foldername', vid, language_override=target_lang)
            if outcome == 'matched': return

        # ── If we collected candidates across tiers, mark as multiple ──
        # Use MatchRepository
        candidates = self.db.matches.get_candidates(file_id)
        if candidates:
            # Use FileRepository
            self.db.files.update_file(file_id, match_status='multiple')
            return

        # ── Tier 5: Hail Mary (no confidence check) ──
        all_unfiltered = []
        seen_ids = set()
        for title, year, source in self.matcher.get_all_search_terms(vid):
            search_type = self.matcher.guess_search_type(vid)
            results = self.matcher.search_api(title, year, search_type, language_override=target_lang)
            for r in results:
                if r['tmdb_id'] not in seen_ids:
                    r['_source'] = source
                    all_unfiltered.append(r)
                    seen_ids.add(r['tmdb_id'])
        
        if len(all_unfiltered) == 1:
            r = all_unfiltered[0]
            status = 'matched' if str(r.get('year')) == str(vid.get('fn_year') or vid.get('fd_year')) else 'uncertain'
            media_item_id = self.library.store_result(r, language_override=target_lang)
            self._finalize_match(file_id, media_item_id, r, vid, status, language_override=target_lang)
        elif len(all_unfiltered) > 1:
            for r in all_unfiltered:
                # Use MatchRepository
                self.db.matches.add_candidate(file_id, r['tmdb_id'], r['title'], r.get('year'),
                                    r['media_type'], r.get('poster_path'), r.get('_source', 'hail_mary'))
            # Use FileRepository
            self.db.files.update_file(file_id, match_status='multiple')
        else:
            # Use FileRepository
            self.db.files.update_file(file_id, match_status='no_match')

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
