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

from api.client import APIClient

logger = logging.getLogger(__name__)


class Resolver:
    """Waterfall matcher: NFO → FFmpeg title → filename → foldername."""

    def __init__(self, db, settings):
        self.db = db
        self.s = settings
        self.api = APIClient(
            omdb_key=settings.omdb_key,
            tmdb_key=settings.tmdb_key,
            tmdb_bearer_token=settings.tmdb_bearer_token,
            db=self.db
        )
        self.language = getattr(settings, 'metadata_language', 'en-US')
        self.fallback_language = getattr(settings, 'fallback_language', '')

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
                outcome = self._evaluate_results(results, title, year, file_id, 'internal_title', vid)
                if outcome == 'matched':
                    return

        # ── Tier 3: Filename GuessIt ──
        if vid['fn_title']:
            search_type = vid['fn_media_type'] or self._guess_search_type(vid)
            results = self._search_api(vid['fn_title'], vid['fn_year'], search_type)
            outcome = self._evaluate_results(results, vid['fn_title'], vid['fn_year'], file_id, 'filename', vid)
            if outcome == 'matched':
                return

        # ── Tier 4: Foldername GuessIt ──
        if vid['fd_title']:
            search_type = vid['fd_media_type'] or self._guess_search_type(vid)
            results = self._search_api(vid['fd_title'], vid['fd_year'], search_type)
            outcome = self._evaluate_results(results, vid['fd_title'], vid['fd_year'], file_id, 'foldername', vid)
            if outcome == 'matched':
                return

        # ── If we collected candidates across tiers, mark as multiple ──
        candidates = self.db.get_candidates(file_id)
        if candidates:
            self.db.update_file(file_id, match_status='multiple')
            return

        # ── Tier 5: Hail Mary (no confidence check) ──
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
            r = all_unfiltered[0]
            status = 'matched' if str(r.get('year')) == str(vid.get('fn_year') or vid.get('fd_year')) else 'uncertain'
            media_item_id = self._store_result(r)
            self._finalize_match(file_id, media_item_id, r, vid, status)
        elif len(all_unfiltered) > 1:
            for r in all_unfiltered:
                self.db.add_candidate(file_id, r['tmdb_id'], r['title'], r.get('year'),
                                    r['media_type'], r.get('poster_path'), r.get('_source', 'hail_mary'))
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
        # 1. Try primary language
        results = self._execute_search(title, year, search_type, self.language)
        
        # 2. If no results and fallback exists, try fallback
        if not results and self.fallback_language:
            logger.debug(f"No results for '{title}' in {self.language}, trying fallback {self.fallback_language}")
            results = self._execute_search(title, year, search_type, self.fallback_language)
            
        return results

    def _execute_search(self, title, year, search_type, language):
        """Helper to perform the actual API call with a specific language."""
        results = []
        year_str = str(year) if year else "unknown"
        
        try:
            if search_type in ('movie', None):
                data = self.api.search_movie(title, year_str, language)
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
                data = self.api.search_tv(title, year_str, language)
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
            logger.warning(f"API Search error for '{title}' in {language}: {e}")
        
        return results

    def _evaluate_results(self, results, search_title, search_year, file_id, source, vid):
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
            res = confident[0]
            media_item_id = self._store_result(res)
            self._finalize_match(file_id, media_item_id, res, vid, 'matched')
            return 'matched'
        
        elif len(confident) > 1:
            # Multiple confident matches → store as candidates (deduped)
            self._add_candidates_deduped(file_id, confident, source)
            return 'multiple'
        
        else:
            # No confident matches
            return 'none'

    def _finalize_match(self, file_id, media_item_id, res, vid, status='matched'):
        """Centralized logic to link file to media and specific episodes."""
        if res['media_type'] == 'tv':
            season_num = vid.get('fn_season') or vid.get('fd_season')
            if season_num is not None:
                # 1. Fetch and store season (populates tv_episodes table)
                self._fetch_and_store_season(res['tmdb_id'], season_num)
                
                # 2. Get episode numbers from filename/folder
                ep_val = vid.get('fn_episode') or vid.get('fd_episode')
                ep_nums = []
                if isinstance(ep_val, (list, tuple)): ep_nums = list(ep_val)
                elif isinstance(ep_val, int): ep_nums = [ep_val]
                elif isinstance(ep_val, str) and ep_val:
                    if ep_val.startswith('['):
                        import ast
                        try:
                            parsed = ast.literal_eval(ep_val)
                            ep_nums = list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]
                        except: pass
                    if not ep_nums:
                        ep_nums = [int(n) for n in re.findall(r'\d+', ep_val)]
                
                # 3. Link each detected episode
                if ep_nums:
                    linked_any = False
                    for ep_num in ep_nums:
                        with self.db._get_connection() as conn:
                            ep_row = conn.execute(
                                "SELECT id FROM tv_episodes WHERE media_item_id = ? AND season_number = ? AND episode_number = ?",
                                (media_item_id, season_num, ep_num)
                            ).fetchone()
                        if ep_row:
                            self.db.link_file_to_media(file_id, media_item_id, status, tv_episode_id=ep_row['id'])
                            linked_any = True
                    
                    if not linked_any:
                        self.db.link_file_to_media(file_id, media_item_id, status)
                else:
                    self.db.link_file_to_media(file_id, media_item_id, status)
            else:
                self.db.link_file_to_media(file_id, media_item_id, status)
        else:
            # Movie logic
            self.db.link_file_to_media(file_id, media_item_id, status)

    def _add_candidates_deduped(self, file_id, results, source):
        """Adds candidates while avoiding duplicates (by tmdb_id)."""
        existing = self.db.get_candidates(file_id)
        existing_ids = {c['tmdb_id'] for c in existing}
        
        for r in results:
            if r['tmdb_id'] not in existing_ids:
                # Pre-store as media item to cache details/posters
                self._store_result(r)
                
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
        
        # If year is a perfect match, we can be much more lenient with the title
        # especially for localized titles (Hungarian vs English)
        exact_year = str(search_year) == str(result_year) if search_year and result_year else False
        
        if exact_year:
            return True # Trust exact year match even if titles differ slightly
            
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
                details_json=json.dumps(data, ensure_ascii=False),
                tmdb_id=data.get('id'),  # Season TMDB ID
                episode_count=data.get('episode_count')
            )
            
            # Pre-download season poster
            if data.get('poster_path'):
                self._pre_download_poster(data['poster_path'])
            
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
                    details_json=json.dumps(ep, ensure_ascii=False),
                    tmdb_id=ep.get('id'),  # Episode TMDB ID
                    vote_count_tmdb=ep.get('vote_count'),
                    imdb_id=ep.get('external_ids', {}).get('imdb_id')
                )
                # Pre-download episode still if available
                if ep.get('still_path'):
                    self._pre_download_poster(ep['still_path'])
                
        except Exception as e:
            logger.warning(f"Season fetch failed for TMDB {tmdb_id} S{season_number}: {e}")

    # ── Helpers ─────────────────────────────────────────────────

    def _store_result(self, result):
        """Saves a match result to media_items with full Pocket Library details."""
        tmdb_id = result['tmdb_id']
        media_type = result['media_type']
        
        # 1. Enrich with FULL details from API (not just search result)
        director = ""
        cast = ""
        rating_tmdb = None
        rating_imdb = None
        rating_rotten = None
        rating_metacritic = None
        votes_imdb = None
        
        # New fields init
        vote_count_tmdb = None
        budget = None
        revenue = None
        runtime = None
        popularity = None
        tagline = ""
        overview = ""
        genres = ""
        original_title = ""
        original_language = ""
        origin_country = ""
        release_date = ""
        first_air_date = ""
        last_air_date = ""
        number_of_episodes = None
        number_of_seasons = None
        languages = ""
        status = ""
        type = ""

        try:
            full_data = self.api.get_from_tmdb(tmdb_id, media_type, self.language)
            if full_data:
                result['details_json'] = json.dumps(full_data, ensure_ascii=False)
                if full_data.get('poster_path'):
                    result['poster_path'] = full_data['poster_path']
                
                if media_type == 'movie' and full_data.get('title'):
                    result['title'] = full_data['title']
                elif media_type == 'tv' and full_data.get('name'):
                    result['title'] = full_data['name']
                
                # Basic Metadata
                rating_tmdb = full_data.get('vote_average')
                vote_count_tmdb = full_data.get('vote_count')
                budget = full_data.get('budget')
                revenue = full_data.get('revenue')
                runtime = full_data.get('runtime')
                popularity = full_data.get('popularity')
                tagline = full_data.get('tagline', '')
                overview = full_data.get('overview', '')
                original_title = full_data.get('original_title') or full_data.get('original_name', '')
                original_language = full_data.get('original_language', '')
                release_date = full_data.get('release_date') or full_data.get('first_air_date', '')
                
                # TV Specifics
                first_air_date = full_data.get('first_air_date', '')
                last_air_date = full_data.get('last_air_date', '')
                number_of_episodes = full_data.get('number_of_episodes')
                number_of_seasons = full_data.get('number_of_seasons')
                status = full_data.get('status', '')
                type = full_data.get('type', '')
                
                lang_list = [l['name'] for l in full_data.get('spoken_languages', [])]
                languages = ", ".join(lang_list)

                if release_date and len(release_date) >= 4:
                    try:
                        result['year'] = int(release_date[:4])
                    except: pass
                
                # Genres (join list)
                genre_list = [g['name'] for g in full_data.get('genres', [])]
                genres = ", ".join(genre_list)
                
                # Origin Country
                countries = full_data.get('origin_country', [])
                if not countries and 'production_countries' in full_data:
                    countries = [c['iso_3166_1'] for c in full_data['production_countries']]
                origin_country = ", ".join(countries) if isinstance(countries, list) else str(countries)

                # Extract Director / Cast
                directors = []
                if media_type == 'movie':
                    crew = full_data.get('credits', {}).get('crew', [])
                    directors = [p['name'] for p in crew if p.get('job') == 'Director']
                else:
                    creators = full_data.get('created_by', [])
                    directors = [p['name'] for p in creators]
                director = ", ".join(directors[:2]) if directors else ""
                
                cast_list = full_data.get('credits', {}).get('cast', [])
                actors = [p['name'] for p in cast_list[:6]]
                cast = ", ".join(actors) if actors else ""

            # 1b. Try OMDB for extra ratings if we have IMDb ID
            imdb_id = result.get('imdb_id')
            if not imdb_id and full_data:
                imdb_id = full_data.get('imdb_id') or full_data.get('external_ids', {}).get('imdb_id')
            
            if imdb_id:
                omdb_data = self.api.get_from_omdb_by_imdb_id(imdb_id)
                if omdb_data and omdb_data.get('Response') != 'False':
                    try: rating_imdb = float(omdb_data.get('imdbRating', 0))
                    except: pass
                    try: rating_metacritic = int(omdb_data.get('Metascore', 0))
                    except: pass
                    try: 
                        v_str = omdb_data.get('imdbVotes', '0').replace(',', '')
                        votes_imdb = int(v_str)
                    except: pass
                    for r in omdb_data.get('Ratings', []):
                        if r['Source'] == 'Rotten Tomatoes':
                            rating_rotten = r['Value']
        except Exception as e:
            logger.warning(f"Full enrichment failed for {media_type} {tmdb_id}: {e}")

        # 2. Save to DB
        item_id = self.db.upsert_media_item(
            tmdb_id=tmdb_id,
            imdb_id=result.get('imdb_id'),
            title=result['title'],
            year=result.get('year'),
            media_type=media_type,
            details_json=result.get('details_json'),
            poster_path=result.get('poster_path'),
            director=director,
            cast=cast,
            rating_tmdb=rating_tmdb,
            rating_imdb=rating_imdb,
            rating_rotten=rating_rotten,
            rating_metacritic=rating_metacritic,
            votes_imdb=votes_imdb,
            vote_count_tmdb=vote_count_tmdb,
            budget=budget,
            revenue=revenue,
            runtime=runtime,
            popularity=popularity,
            tagline=tagline,
            overview=overview,
            genres=genres,
            original_title=original_title,
            original_language=original_language,
            origin_country=origin_country,
            release_date=release_date,
            first_air_date=first_air_date,
            last_air_date=last_air_date,
            number_of_episodes=number_of_episodes,
            number_of_seasons=number_of_seasons,
            languages=languages,
            status=status,
            type=type
        )
        
        # 3. Pre-download poster to cache
        if result.get('poster_path'):
            self._pre_download_poster(result['poster_path'])
            
        # 4. TV Logic: Fetch ALL seasons/episodes for the Pocket Library
        if media_type == 'tv':
            try:
                # We already have full_data from step 1
                details = json.loads(result.get('details_json', '{}'))
                if details and 'seasons' in details:
                    for s in details['seasons']:
                        s_num = s.get('season_number')
                        if s_num is not None:
                            self._fetch_and_store_season(tmdb_id, s_num)
            except Exception as e:
                logger.warning(f"Season hydration failed for TMDB {tmdb_id}: {e}")
            
        return item_id

    def _pre_download_poster(self, poster_path):
        """Downloads poster to local cache if not already there."""
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))
        
        if not os.path.exists(local_path):
            try:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                url = f"https://image.tmdb.org/t/p/w500{poster_path}" # Use w500 to match UI
                r = self.api.session.get(url, timeout=5)
                if r.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(r.content)
            except Exception:
                pass

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

