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
        self.language = getattr(settings, 'metadata_language', 'en-US')
        self._download_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self._omdb_auth_failed = False # Track 401 errors to avoid spamming
        self._enriched_ids = set() # Track items enriched in this session

    def store_result(self, result):
        """
        Enriches TMDB search result with full details and saves to media_items.
        Returns the new/existing media_item_id.
        """
        tmdb_id = result['tmdb_id']
        media_type = result['media_type']
        
        # Check if already enriched in this session or exists in DB with details
        if tmdb_id in self._enriched_ids:
            item = self.db.media.get_media_item_by_tmdb_id(tmdb_id)
            if item: return item['id']

        existing = self.db.media.get_media_item_by_tmdb_id(tmdb_id)
        if existing and existing.get('details_json'):
            self._enriched_ids.add(tmdb_id)
            return existing['id']

        # Enrichment variables
        director = ""
        cast = ""
        rating_tmdb = None
        rating_imdb = None
        rating_rotten = None
        rating_metacritic = None
        votes_imdb = None
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
        imdb_id = result.get('imdb_id', '')
        full_data = None

        # 1. TMDB Detail enrichment
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
                    try:
                        result['year'] = int(release_date[:4])
                    except: pass
                
                genre_list = [g['name'] for g in full_data.get('genres', [])]
                genres = ", ".join(genre_list)
                
                countries = full_data.get('origin_country', [])
                if not countries and 'production_countries' in full_data:
                    countries = [c['iso_3166_1'] for c in full_data['production_countries']]
                origin_country = ", ".join(countries) if isinstance(countries, list) else str(countries)

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
                
                if not imdb_id:
                    imdb_id = full_data.get('imdb_id') or full_data.get('external_ids', {}).get('imdb_id', '')

        except Exception as e:
            logger.warning(f"TMDB enrichment failed for {media_type} {tmdb_id}: {e}")

        # 2. OMDB enrichment
        if not self._omdb_auth_failed:
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
                # Catch 401/403 to stop spamming
                if "401" in str(e) or "403" in str(e) or "Authentication failed" in str(e):
                    self._omdb_auth_failed = True
                    logger.error(f"OMDB enrichment disabled: {e}. Please check your API key in settings.")
                else:
                    logger.warning(f"OMDB enrichment failed for {media_type} {tmdb_id}: {e}")

        # 3. Save to DB using MediaRepository
        media_data = {
            'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'title': result['title'],
            'year': result.get('year'), 'media_type': media_type,
            'details_json': result.get('details_json'), 'poster_path': result.get('poster_path'),
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
            'status': status, 'type': type
        }
        item_id = self.db.media.upsert_media_item(**media_data)
        self._enriched_ids.add(tmdb_id)
        
        # 4. Pre-download poster
        if result.get('poster_path'):
            self.pre_download_poster(result['poster_path'])
            
        # 5. TV Logic: Fetch ALL seasons/episodes for TV shows
        if media_type == 'tv':
            try:
                details = json.loads(result.get('details_json', '{}'))
                if details and 'seasons' in details:
                    for s in details['seasons']:
                        s_num = s.get('season_number')
                        if s_num is not None:
                            self.fetch_and_store_season(tmdb_id, s_num)
            except Exception as e:
                logger.warning(f"Season hydration failed for TMDB {tmdb_id}: {e}")
            
        return item_id

    def fetch_and_store_season(self, tmdb_id, season_number):
        """Fetches a full season from TMDB and stores episodes."""
        try:
            data = self.api.tmdb.get_season_details(tmdb_id, season_number, self.language)
            if not data:
                return
            
            # Use MediaRepository to find the item
            media_item = self.db.media.get_media_item_by_tmdb_id(tmdb_id)
            if not media_item: return
            media_item_id = media_item['id']
            
            season_data = {
                'media_item_id': media_item_id, 'season_number': season_number,
                'name': data.get('name', ''), 'overview': data.get('overview', ''),
                'poster_path': data.get('poster_path'), 'air_date': data.get('air_date', ''),
                'details_json': json.dumps(data, ensure_ascii=False),
                'tmdb_id': data.get('id'), 'episode_count': data.get('episode_count')
            }
            season_id = self.db.media.upsert_season(**season_data)
            
            if data.get('poster_path'):
                self.pre_download_poster(data['poster_path'])
            
            for ep in data.get('episodes', []):
                ep_num = ep.get('episode_number')
                
                # Check if external_ids were included in the bulk response (rare but possible in some API versions)
                imdb_id = ep.get('external_ids', {}).get('imdb_id')
                
                episode_data = {
                    'season_id': season_id, 'media_item_id': media_item_id,
                    'season_number': season_number, 'episode_number': ep_num,
                    'name': ep.get('name', ''), 'overview': ep.get('overview', ''),
                    'air_date': ep.get('air_date', ''), 'runtime': ep.get('runtime'),
                    'still_path': ep.get('still_path'), 'vote_average': ep.get('vote_average'),
                    'details_json': json.dumps(ep, ensure_ascii=False),
                    'tmdb_id': ep.get('id'), 'vote_count_tmdb': ep.get('vote_count'),
                    'imdb_id': imdb_id
                }
                self.db.media.upsert_episode(**episode_data)
                if ep.get('still_path'):
                    self.pre_download_poster(ep['still_path'])
                
        except Exception as e:
            logger.warning(f"Season fetch failed for TMDB {tmdb_id} S{season_number}: {e}")

    def pre_download_poster(self, poster_path):
        """Initiates an asynchronous background download for a poster."""
        if not poster_path: return
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cache_dir = os.path.join(base_dir, 'data', 'cache', 'posters')
        local_path = os.path.join(cache_dir, poster_path.lstrip('/'))
        
        if not os.path.exists(local_path):
            url = f"https://image.tmdb.org/t/p/w500{poster_path}"
            self._download_executor.submit(self._do_download, url, local_path)

    def _do_download(self, url, local_path):
        """The actual synchronous download task run in a background thread."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            r = self.api.session.get(url, timeout=10)
            if r.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(r.content)
                logger.debug(f"Downloaded poster: {os.path.basename(local_path)}")
        except Exception as e:
            logger.debug(f"Poster download failed: {e}")
