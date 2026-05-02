"""
v3.0 Resolver: Matches files to TMDB metadata using a waterfall strategy.

Matching order:
  1. NFO IMDB ID  → /find → always 1 result → DONE
  2. FFmpeg title → /search → confidence check → waterfall
  3. Filename GuessIt → /search → confidence check → waterfall
  4. Foldername GuessIt → /search → confidence check → waterfall

Results:
  - 'matched'  → single confident match, linked to media_items
  - 'multiple' → candidates stored in match_candidates table
  - 'no_match' → nothing found
"""

import re
import json
import logging
import unicodedata

from utils.api_client import APIClient

logger = logging.getLogger(__name__)


class Resolver:
    """Waterfall matcher: NFO → FFmpeg title → filename → foldername."""

    def __init__(self, db, settings):
        self.db = db
        self.s = settings
        self.api = APIClient(
            omdb_key=settings.omdb_key,
            tmdb_key=settings.tmdb_key,
            tmdb_bearer_token=settings.tmdb_bearer_token
        )
        self.language = getattr(settings, 'metadata_language', 'hu-HU')

    def resolve_all(self, progress_callback=None):
        """Runs the full matching pipeline concurrently on all unmatched parent videos."""
        import concurrent.futures
        
        videos = self.db.get_files_by_category('video')
        unmatched = [v for v in videos if v['match_status'] == 'pending']
        
        completed = 0
        total = len(unmatched)
        
        # Max 5-8 workers is optimal for TMDB API without hitting rate limits
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._resolve_single, vid): vid for vid in unmatched}
            
            for future in concurrent.futures.as_completed(futures):
                vid = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error resolving {vid['file_name']}: {e}")
                
                completed += 1
                if progress_callback:
                    progress_callback(f"Resolved: {vid['file_name']}", completed, total)

    def _resolve_single(self, vid):
        """Runs the waterfall for a single file."""
        file_id = vid['id']

        # ── Tier 1: NFO IMDB ID (trusted, no confidence check) ──
        if vid['nfo_imdb_id']:
            result = self._resolve_by_imdb(vid['nfo_imdb_id'])
            if result:
                media_item_id = self._store_result(result)
                self.db.link_file_to_media(file_id, media_item_id, 'matched')
                self._fetch_tv_details_if_needed(result, vid)
                return

        # ── Tier 2: FFmpeg internal title ──
        if vid['internal_title']:
            title, year = self._parse_title_year(vid['internal_title'])
            if title:
                search_type = self._guess_search_type(vid)
                results = self._search_api(title, year, search_type)
                outcome = self._evaluate_results(results, title, year, file_id, 'internal_title')
                if outcome == 'matched':
                    self._fetch_tv_details_if_needed_from_file(file_id, vid)
                    return
                # If multiple or 0, continue waterfall

        # ── Tier 3: Filename GuessIt ──
        if vid['fn_title']:
            search_type = vid['fn_media_type'] or self._guess_search_type(vid)
            results = self._search_api(vid['fn_title'], vid['fn_year'], search_type)
            outcome = self._evaluate_results(results, vid['fn_title'], vid['fn_year'], file_id, 'filename')
            if outcome == 'matched':
                self._fetch_tv_details_if_needed_from_file(file_id, vid)
                return

        # ── Tier 4: Foldername GuessIt ──
        if vid['fd_title']:
            search_type = vid['fd_media_type'] or self._guess_search_type(vid)
            results = self._search_api(vid['fd_title'], vid['fd_year'], search_type)
            outcome = self._evaluate_results(results, vid['fd_title'], vid['fd_year'], file_id, 'foldername')
            if outcome == 'matched':
                self._fetch_tv_details_if_needed_from_file(file_id, vid)
                return

        # ── If we collected candidates across tiers, mark as multiple ──
        candidates = self.db.get_candidates(file_id)
        if candidates:
            self.db.update_file(file_id, match_status='multiple')
            return

        # ── Tier 5: Hail Mary (no confidence check) ──
        # Re-run searches without filtering, collect anything we get
        all_unfiltered = []
        seen_ids = set()
        
        for title, year, source in self._get_all_search_terms(vid):
            search_type = self._guess_search_type(vid)
            results = self._search_api(title, year, search_type)
            for r in results:
                if r['tmdb_id'] not in seen_ids:
                    r['_source'] = source
                    all_unfiltered.append(r)
                    seen_ids.add(r['tmdb_id'])
        
        if len(all_unfiltered) == 1:
            # Single unfiltered result → uncertain (user confirms)
            r = all_unfiltered[0]
            media_item_id = self._store_result(r)
            self.db.link_file_to_media(file_id, media_item_id, 'uncertain')
            self._fetch_tv_details_if_needed(r, vid)
        elif len(all_unfiltered) > 1:
            # Multiple unfiltered → candidates
            for r in all_unfiltered:
                self.db.add_candidate(
                    file_id, r['tmdb_id'], r['title'], r.get('year'),
                    r['media_type'], r.get('poster_path'), r.get('_source', 'hail_mary')
                )
            self.db.update_file(file_id, match_status='multiple')
        else:
            self.db.update_file(file_id, match_status='no_match')

    # ── IMDB Resolution ────────────────────────────────────────

    def _resolve_by_imdb(self, imdb_id):
        """Uses /find endpoint to get TMDB data from IMDB ID. Always trusted."""
        try:
            data = self.api.get_by_external_id(imdb_id, language=self.language)
            
            # Check movie results first
            movies = data.get('movie_results', [])
            if movies:
                m = movies[0]
                return {
                    'tmdb_id': m['id'],
                    'imdb_id': imdb_id,
                    'title': m.get('title', ''),
                    'year': self._extract_year(m.get('release_date', '')),
                    'media_type': 'movie',
                    'poster_path': m.get('poster_path'),
                    'details_json': json.dumps(m, ensure_ascii=False)
                }
            
            # Check TV results
            tv = data.get('tv_results', [])
            if tv:
                t = tv[0]
                return {
                    'tmdb_id': t['id'],
                    'imdb_id': imdb_id,
                    'title': t.get('name', ''),
                    'year': self._extract_year(t.get('first_air_date', '')),
                    'media_type': 'tv',
                    'poster_path': t.get('poster_path'),
                    'details_json': json.dumps(t, ensure_ascii=False)
                }
                
        except Exception as e:
            logger.warning(f"IMDB resolve failed for {imdb_id}: {e}")
        
        return None

    # ── Title-based Search ──────────────────────────────────────

    def _search_api(self, title, year, search_type):
        """Searches TMDB by title+year. Returns list of result dicts."""
        results = []
        year_str = str(year) if year else "unknown"
        
        try:
            if search_type in ('movie', None):
                data = self.api.search_movie(title, year_str, self.language)
                for r in data.get('results', [])[:5]:
                    results.append({
                        'tmdb_id': r['id'],
                        'title': r.get('title', ''),
                        'year': self._extract_year(r.get('release_date', '')),
                        'media_type': 'movie',
                        'poster_path': r.get('poster_path'),
                        'details_json': json.dumps(r, ensure_ascii=False)
                    })
            
            if search_type in ('episode', 'tv', None):
                data = self.api.search_tv(title, year_str, self.language)
                for r in data.get('results', [])[:5]:
                    results.append({
                        'tmdb_id': r['id'],
                        'title': r.get('name', ''),
                        'year': self._extract_year(r.get('first_air_date', '')),
                        'media_type': 'tv',
                        'poster_path': r.get('poster_path'),
                        'details_json': json.dumps(r, ensure_ascii=False)
                    })
        except Exception as e:
            logger.warning(f"Search failed for '{title}' ({year}): {e}")
        
        return results

    def _evaluate_results(self, results, search_title, search_year, file_id, source):
        """
        Evaluates search results with confidence check.
        Returns 'matched', 'multiple', or 'none'.
        """
        if not results:
            return 'none'

        # Filter by confidence
        confident = [r for r in results if self._confidence_check(r, search_title, search_year)]

        if len(confident) == 1:
            # Single confident match → DONE
            media_item_id = self._store_result(confident[0])
            self.db.link_file_to_media(file_id, media_item_id, 'matched')
            return 'matched'
        
        elif len(confident) > 1:
            # Multiple confident matches → store as candidates (deduped)
            self._add_candidates_deduped(file_id, confident, source)
            return 'multiple'
        
        else:
            # No confident matches
            return 'none'

    def _add_candidates_deduped(self, file_id, results, source):
        """Adds candidates while avoiding duplicates (by tmdb_id)."""
        existing = self.db.get_candidates(file_id)
        existing_ids = {c['tmdb_id'] for c in existing}
        
        for r in results:
            if r['tmdb_id'] not in existing_ids:
                self.db.add_candidate(
                    file_id, r['tmdb_id'], r['title'], r['year'],
                    r['media_type'], r.get('poster_path'), source
                )
                existing_ids.add(r['tmdb_id'])

    # ── Confidence Check ────────────────────────────────────────

    def _confidence_check(self, result, search_title, search_year):
        """Returns True if the result is a confident match."""
        result_title = result.get('title', '')
        result_year = result.get('year')
        
        # Title check: normalized containment
        norm_search = self._normalize(search_title)
        norm_result = self._normalize(result_title)
        
        if not norm_search or not norm_result:
            return False
        
        title_ok = (norm_search in norm_result) or (norm_result in norm_search)
        
        if not title_ok:
            return False
        
        # Year check (if we have a year to compare)
        if search_year and result_year:
            try:
                if abs(int(search_year) - int(result_year)) > 1:
                    return False
            except (ValueError, TypeError):
                pass
        
        return True

    # ── TV Season/Episode Details ───────────────────────────────

    def _fetch_tv_details_if_needed(self, result, vid):
        """If the result is TV and we know the season, fetch season details."""
        if result.get('media_type') != 'tv':
            return
        
        tmdb_id = result['tmdb_id']
        season_num = vid.get('fn_season') or vid.get('fd_season')
        
        if season_num is not None:
            self._fetch_and_store_season(tmdb_id, season_num)

    def _fetch_tv_details_if_needed_from_file(self, file_id, vid):
        """Fetches TV details based on the file's linked media_item."""
        file_data = self.db.get_file_by_id(file_id)
        if not file_data or not file_data.get('media_item_id'):
            return
        
        # Get the media item to check type
        with self.db._get_connection() as conn:
            item = conn.execute(
                "SELECT * FROM media_items WHERE id = ?", (file_data['media_item_id'],)
            ).fetchone()
        
        if not item or item['media_type'] != 'tv':
            return
        
        season_num = vid.get('fn_season') or vid.get('fd_season')
        if season_num is not None:
            self._fetch_and_store_season(item['tmdb_id'], season_num)

    def _fetch_and_store_season(self, tmdb_id, season_number):
        """Fetches a full season from TMDB and stores episodes."""
        try:
            data = self.api.get_from_tmdb_season(tmdb_id, season_number, self.language)
            if not data:
                return
            
            # Get or create media_item_id for this series
            with self.db._get_connection() as conn:
                row = conn.execute("SELECT id FROM media_items WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
            
            if not row:
                return
            
            media_item_id = row['id']
            
            # Store season
            season_id = self.db.upsert_season(
                media_item_id=media_item_id,
                season_number=season_number,
                name=data.get('name', ''),
                overview=data.get('overview', ''),
                poster_path=data.get('poster_path'),
                air_date=data.get('air_date', ''),
                details_json=json.dumps(data, ensure_ascii=False)
            )
            
            # Store episodes
            for ep in data.get('episodes', []):
                self.db.upsert_episode(
                    season_id=season_id,
                    media_item_id=media_item_id,
                    season_number=season_number,
                    episode_number=ep.get('episode_number'),
                    name=ep.get('name', ''),
                    overview=ep.get('overview', ''),
                    air_date=ep.get('air_date', ''),
                    runtime=ep.get('runtime'),
                    still_path=ep.get('still_path'),
                    vote_average=ep.get('vote_average'),
                    details_json=json.dumps(ep, ensure_ascii=False)
                )
                
        except Exception as e:
            logger.warning(f"Season fetch failed for TMDB {tmdb_id} S{season_number}: {e}")

    # ── Helpers ─────────────────────────────────────────────────

    def _store_result(self, result):
        """Saves a match result to media_items. Returns the media_item_id."""
        return self.db.upsert_media_item(
            tmdb_id=result['tmdb_id'],
            imdb_id=result.get('imdb_id'),
            title=result['title'],
            year=result.get('year'),
            media_type=result['media_type'],
            details_json=result.get('details_json'),
            poster_path=result.get('poster_path')
        )

    def _guess_search_type(self, vid):
        """Guesses whether to search movie or TV based on available data."""
        if vid.get('fn_season') is not None or vid.get('fd_season') is not None:
            return 'episode'
        if vid.get('fn_media_type') == 'episode' or vid.get('fd_media_type') == 'episode':
            return 'episode'
        return None  # Search both

    def _parse_title_year(self, raw_title):
        """Splits 'Title (2006)' into ('Title', 2006)."""
        match = re.match(r'(.+?)\s*\((\d{4})\)\s*$', raw_title)
        if match:
            return match.group(1).strip(), int(match.group(2))
        return raw_title.strip(), None

    def _extract_year(self, date_str):
        """Extracts year from '2010-07-16' format."""
        if date_str and len(date_str) >= 4:
            try:
                return int(date_str[:4])
            except ValueError:
                pass
        return None

    def _normalize(self, text):
        """Normalizes text for comparison: lowercase, strip accents and punctuation."""
        if not text:
            return ''
        # Remove accents
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        # Lowercase, strip punctuation
        text = re.sub(r'[^a-z0-9\s]', '', text.lower())
        return text.strip()

    def _get_all_search_terms(self, vid):
        """Yields all available (title, year, source) tuples for searching."""
        # Internal title
        if vid.get('internal_title'):
            title, year = self._parse_title_year(vid['internal_title'])
            if title:
                yield (title, year, 'internal_title')
        
        # Filename GuessIt
        if vid.get('fn_title'):
            yield (vid['fn_title'], vid.get('fn_year'), 'filename')
        
        # Foldername GuessIt
        if vid.get('fd_title'):
            yield (vid['fd_title'], vid.get('fd_year'), 'foldername')

