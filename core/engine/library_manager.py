import json
import logging
import os
import concurrent.futures
from api.client import APIClient

logger = logging.getLogger(__name__)

class LibraryManager:
    """
    Handles persistence and enrichment of media data in the database.
    Responsible for:
    - Upserting media items, seasons, and episodes.
    - Linking files to media.
    - Fetching full details (enrichment) from TMDB and OMDB.
    - Managing local asset cache (posters).
    """

    def __init__(self, db, settings):
        self.db = db
        self.s = settings
        self.api = APIClient(
            omdb_key=settings.omdb_key,
            tmdb_key=settings.tmdb_key,
            tmdb_bearer_token=settings.tmdb_bearer_token,
            db=self.db
        )
        self._download_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self._omdb_auth_failed = False 
        self._omdb_limit_reached = False
        self._enriched_ids = set()

    def refresh_settings(self, settings):
        """Re-initializes API client with new settings."""
        self.s = settings
        from api.client import APIClient
        self.api = APIClient(
            omdb_key=settings.omdb_key,
            tmdb_key=settings.tmdb_key,
            tmdb_bearer_token=settings.tmdb_bearer_token,
            db=self.db
        )

    @property
    def language(self):
        """Always get the current language from settings."""
        return getattr(self.s, 'metadata_language', 'en-US')

    def store_result(self, result, language_override=None, force_refresh=False, priority_seasons=None):
        """
        Enriches TMDB search result with full details and saves to media_items.
        Returns the new/existing media_item_id.
        """
        tmdb_id = result['tmdb_id']
        media_type = result['media_type']
        target_lang = language_override or self.language
        
        existing = self.db.media.get_media_item_by_tmdb_id(tmdb_id)
        fetched = (existing.get('fetched_languages') or "") if existing else ""
        fetched_list = [l.strip() for l in fetched.split(',') if l.strip()]
        
        # Determine if we need to fetch from TMDB
        # (Always fetch if force_refresh or if language not yet fetched)
        needs_tmdb = force_refresh or target_lang not in fetched_list

        # ... (rest of metadata extraction logic remains similar, but use priority_seasons)
        # For brevity, I'll keep the core logic but optimize the season loop at the end
        
        # [Simplified for replacement, but ensuring core logic is preserved]
        # (I will use multi_replace if I need to change many parts, but let's try to fit the logic)
        
        # Actually, let's keep the existing logic but just fix the loop at the end.
        # I'll re-read the middle part to make sure I don't break anything.
        # Line 58 to 226 is the core metadata extraction.
        
        # Let's do it properly. I'll use multi_replace for safety.
        
        # Robust check: if it's a TV show, we might need to refresh seasons/episodes even if series exists
        is_tv = result.get('media_type') == 'tv' or (existing and existing.get('media_type') == 'tv')
        if existing and target_lang in fetched_list and not is_tv and not force_refresh:
            return existing['id']

        # Enrichment
        director = existing.get('director', "") if existing else ""
        cast = existing.get('cast', "") if existing else ""
        rating_tmdb = existing.get('rating_tmdb') if existing else None
        rating_imdb = existing.get('rating_imdb') if existing else None
        rating_rotten = existing.get('rating_rotten', "") if existing else ""
        rating_metacritic = existing.get('rating_metacritic') if existing else None
        votes_imdb = existing.get('votes_imdb') if existing else None
        vote_count_tmdb = existing.get('vote_count_tmdb') if existing else None
        budget = existing.get('budget') if existing else None
        revenue = existing.get('revenue') if existing else None
        runtime = existing.get('runtime') if existing else None
        popularity = existing.get('popularity') if existing else None
        tagline = existing.get('tagline', "") if existing else ""
        overview = existing.get('overview', "") if existing else ""
        genres = existing.get('genres', "") if existing else ""
        original_title = existing.get('original_title', "") if existing else ""
        original_language = existing.get('original_language', "") if existing else ""
        origin_country = existing.get('origin_country', "") if existing else ""
        release_date = existing.get('release_date', "") if existing else ""
        first_air_date = existing.get('first_air_date', "") if existing else ""
        last_air_date = existing.get('last_air_date', "") if existing else ""
        number_of_episodes = existing.get('number_of_episodes') if existing else None
        number_of_seasons = existing.get('number_of_seasons') if existing else None
        languages = existing.get('languages', "") if existing else ""
        status = existing.get('status', "") if existing else ""
        type = existing.get('type', "") if existing else ""
        imdb_id = result.get('imdb_id', '') or (existing.get('imdb_id') if existing else "")
        networks = result.get('networks') or (existing.get('networks') if existing else "")
        collection = result.get('collection') or (existing.get('collection') if existing else "")
        
        full_data = None
        try:
            full_data = self.api.get_from_tmdb(tmdb_id, media_type, target_lang)
            if full_data:
                details_json = {}
                if existing and existing.get('details_json'):
                    try:
                        details_json = json.loads(existing['details_json'])
                        if not isinstance(details_json, dict) or 'tmdb_id' in details_json:
                            details_json = { "en-US": details_json }
                    except: pass
                
                details_json[target_lang] = full_data
                result['details_json'] = json.dumps(details_json, ensure_ascii=False)
                
                if full_data.get('poster_path'):
                    result['poster_path'] = full_data['poster_path']
                
                if media_type == 'movie' and full_data.get('title'):
                    result['title'] = full_data['title']
                elif media_type == 'tv' and full_data.get('name'):
                    result['title'] = full_data['name']
                
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
                first_air_date = full_data.get('first_air_date', '')
                last_air_date = full_data.get('last_air_date', '')
                number_of_episodes = full_data.get('number_of_episodes')
                number_of_seasons = full_data.get('number_of_seasons')
                status = full_data.get('status', '')
                type = full_data.get('type', '')
                
                lang_list = [l['name'] for l in full_data.get('spoken_languages', [])]
                languages = ", ".join(lang_list)
                if release_date and len(release_date) >= 4:
                    try: result['year'] = int(release_date[:4])
                    except: pass
                
                genre_list = [g['name'] for g in full_data.get('genres', [])]
                genres = ", ".join(genre_list)
                
                countries = full_data.get('origin_country', [])
                if not countries and full_data.get('production_countries'):
                    countries = [c['iso_3166_1'] for c in full_data['production_countries']]
                origin_country = ", ".join(countries) if isinstance(countries, list) else str(countries)

                directors = []
                if media_type == 'movie':
                    crew = (full_data.get('credits') or {}).get('crew', [])
                    directors = [p['name'] for p in crew if p.get('job') == 'Director']
                else:
                    creators = full_data.get('created_by', [])
                    directors = [p['name'] for p in creators]
                director = ", ".join(directors[:2]) if directors else ""
                
                cast_list = (full_data.get('credits') or {}).get('cast', [])
                actors = [p['name'] for p in cast_list[:6]]
                cast = ", ".join(actors) if actors else ""
                
                if full_data.get('networks'):
                    networks = ", ".join([n['name'] for n in full_data['networks']])
                
                if full_data.get('belongs_to_collection'):
                    collection = full_data['belongs_to_collection'].get('name')
                
                if not imdb_id:
                    imdb_id = full_data.get('imdb_id') or (full_data.get('external_ids') or {}).get('imdb_id', '')

        except Exception as e:
            logger.warning(f"TMDB enrichment failed for {media_type} {tmdb_id}: {e}")

        if not self._omdb_auth_failed and not self._omdb_limit_reached:
            try:
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
                if "401" in str(e) or "403" in str(e):
                    self._omdb_auth_failed = True
                if "limit reached" in str(e).lower():
                    self._omdb_limit_reached = True
                    logger.error("OMDb API Limit Reached! Further enrichment will be skipped for this session.")
                logger.warning(f"OMDB enrichment failed: {e}")

        # Only mark as fetched if we actually got data from TMDB
        if full_data and target_lang not in fetched_list:
            fetched_list.append(target_lang)
        fetched_languages = ", ".join(fetched_list)

        media_data = {
            'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'title': result.get('title') or (existing.get('title') if existing else ""),
            'year': result.get('year') or (existing.get('year') if existing else None), 'media_type': media_type,
            'details_json': result.get('details_json') or (existing.get('details_json') if existing else ""), 
            'poster_path': result.get('poster_path') or (existing.get('poster_path') if existing else ""),
            'director': director, 'cast': cast, 'rating_tmdb': rating_tmdb,
            'rating_imdb': rating_imdb, 'rating_rotten': rating_rotten,
            'rating_metacritic': rating_metacritic, 'votes_imdb': votes_imdb,
            'vote_count_tmdb': vote_count_tmdb, 'budget': budget, 'revenue': revenue,
            'runtime': runtime, 'popularity': popularity, 'tagline': tagline,
            'overview': overview, 'genres': genres, 'original_title': original_title,
            'original_language': original_language, 'origin_country': origin_country,
            'release_date': release_date, 'first_air_date': first_air_date,
            'last_air_date': last_air_date, 'number_of_episodes': number_of_episodes,
            'number_of_seasons': number_of_seasons, 'languages': languages,
            'status': status, 'type': type, 'fetched_languages': fetched_languages,
            'networks': networks, 'collection': collection
        }
        item_id = self.db.media.upsert_media_item(**media_data)
        self._enriched_ids.add(tmdb_id)
        
        if result.get('poster_path'):
            self.pre_download_poster(result['poster_path'])
            
        if media_type == 'tv':
            try:
                details_all = json.loads(media_data.get('details_json', '{}'))
                l_key = target_lang
                if isinstance(details_all, dict) and l_key not in details_all:
                    l_key = l_key.split('-')[0]
                
                details = details_all.get(l_key) if isinstance(details_all, dict) else details_all
                if details and 'seasons' in details:
                    # Sort seasons: priority first, then numeric
                    all_seasons = details['seasons']
                    priority = set(priority_seasons or [])
                    
                    # Group by priority
                    p_list = []
                    others = []
                    for s in all_seasons:
                        s_num = s.get('season_number')
                        if s_num is None: continue
                        if s_num in priority: p_list.append(s_num)
                        else: others.append(s_num)
                    
                    # Fetch in parallel (priority first)
                    # We use a small pool for SQLite safety
                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                        # 1. Priority seasons
                        if p_list:
                            list(executor.map(lambda sn: self.fetch_and_store_season(tmdb_id, sn, target_lang, force_refresh=force_refresh), p_list))
                        
                        # 2. Others (in background/parallel)
                        executor.map(lambda sn: self.fetch_and_store_season(tmdb_id, sn, target_lang, force_refresh=force_refresh), others)
            except Exception as e:
                logger.warning(f"Season hydration failed: {e}")
            
        return item_id

    def fetch_and_store_season(self, tmdb_id, season_number, language_override=None, force_refresh=False):
        """Fetches a full season from TMDB and stores episodes."""
        try:
            target_lang = language_override or self.language
            existing_season = self.db.media.get_season_by_number_by_tmdb_id(tmdb_id, season_number)
            fetched = (existing_season.get('fetched_languages') or "") if existing_season else ""
            fetched_list = [l.strip() for l in fetched.split(',') if l.strip()]
            
            # Skip only if not forced and already fetched in this lang
            if existing_season and target_lang in fetched_list and not force_refresh:
                return existing_season['id']

            data = self.api.tmdb.get_season_details(tmdb_id, season_number, target_lang)
            if not data: return
            
            media_item = self.db.media.get_media_item_by_tmdb_id(tmdb_id)
            if not media_item: return
            media_item_id = media_item['id']
            
            details_json = {}
            if existing_season and existing_season.get('details_json'):
                try:
                    details_json = json.loads(existing_season['details_json'])
                    if not isinstance(details_json, dict) or 'id' in details_json:
                        details_json = { "en-US": details_json }
                except: pass
            details_json[target_lang] = data
            
            if target_lang not in fetched_list:
                fetched_list.append(target_lang)
            fetched_languages = ", ".join(fetched_list)

            season_data = {
                'media_item_id': media_item_id, 'season_number': season_number,
                'name': data.get('name', ''), 'overview': data.get('overview', ''),
                'poster_path': data.get('poster_path'), 'air_date': data.get('air_date', ''),
                'details_json': json.dumps(details_json, ensure_ascii=False),
                'tmdb_id': data.get('id'), 'episode_count': data.get('episode_count'),
                'fetched_languages': fetched_languages
            }
            season_id = self.db.media.upsert_season(**season_data)
            
            # Pre-download season poster
            if season_data['poster_path']:
                self.pre_download_poster(season_data['poster_path'])
            
            for ep in data.get('episodes', []):
                ep_num = ep.get('episode_number')
                existing_ep = self.db.media.get_episode_by_id_fields(media_item_id, season_number, ep_num)
                ep_fetched = (existing_ep.get('fetched_languages') or "") if existing_ep else ""
                ep_fetched_list = [l.strip() for l in ep_fetched.split(',') if l.strip()]
                
                ep_details = {}
                if existing_ep and existing_ep.get('details_json'):
                    try:
                        ep_details = json.loads(existing_ep['details_json'])
                        if not isinstance(ep_details, dict) or 'id' in ep_details:
                            ep_details = { "en-US": ep_details }
                    except: pass
                ep_details[target_lang] = ep
                
                if target_lang not in ep_fetched_list:
                    ep_fetched_list.append(target_lang)
                ep_fetched_languages = ", ".join(ep_fetched_list)

                episode_data = {
                    'season_id': season_id, 'media_item_id': media_item_id,
                    'season_number': season_number, 'episode_number': ep_num,
                    'name': ep.get('name', ''), 'overview': ep.get('overview', ''),
                    'air_date': ep.get('air_date', ''), 'runtime': ep.get('runtime'),
                    'still_path': ep.get('still_path'), 'vote_average': ep.get('vote_average'),
                    'details_json': json.dumps(ep_details, ensure_ascii=False),
                    'tmdb_id': ep.get('id'), 'vote_count_tmdb': ep.get('vote_count'),
                    'imdb_id': ep.get('external_ids', {}).get('imdb_id') or (existing_ep.get('imdb_id') if existing_ep else ""),
                    'fetched_languages': ep_fetched_languages
                }
                self.db.media.upsert_episode(**episode_data)
                
                # Pre-download episode still
                if episode_data['still_path']:
                    self.pre_download_poster(episode_data['still_path'])

        except Exception as e:
            logger.warning(f"Season fetch failed: {e}")

    def pre_download_poster(self, poster_path):
        """Initiates background download for a poster."""
        if not poster_path: return
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))
        if not os.path.exists(local_path):
            url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            self._download_executor.submit(self._do_download, url, local_path)

    def _do_download(self, url, local_path):
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            r = self.api.session.get(url, timeout=10)
            if r.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(r.content)
        except: pass
