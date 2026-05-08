import logging
from api.tmdb_client import TMDBClient
from api.omdb_client import OMDBClient
from api.base_provider import ProviderResult

logger = logging.getLogger(__name__)

class APIClient:
    """
    Facade class that aggregates TMDB and OMDB clients for backward compatibility.
    """
    def __init__(self, omdb_key, tmdb_key, tmdb_bearer_token, db=None):
        self.tmdb = TMDBClient(tmdb_key, tmdb_bearer_token, db)
        self.omdb = OMDBClient(omdb_key, db)
        
        # Unified Provider List
        self.providers = [self.tmdb, self.omdb]

    @property
    def session(self):
        """Always return the shared session from the underlying clients."""
        return self.tmdb._session

    def search_unified(self, query, year=None, media_type='movie', language='hu-HU'):
        """Aggregates results from all providers."""
        all_results = []
        seen_ids = set()
        
        for provider in self.providers:
            try:
                results = provider.search(query, year, media_type, language)
                for res in results:
                    # Avoid duplicates (by TMDB ID or IMDb ID)
                    uid = res.tmdb_id or res.imdb_id
                    if uid not in seen_ids:
                        all_results.append(res)
                        seen_ids.add(uid)
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} search failed: {e}")
        
        return all_results

    def get_from_omdb_by_imdb_id(self, imdb_id):
        return self.omdb.get_by_imdb_id(imdb_id)

    def get_by_external_id(self, external_id, source="imdb_id", language="hu-HU"):
        return self.tmdb.get_by_external_id(external_id, source, language)

    def get_external_id_raw(self, external_id, source="imdb_id", language="hu-HU"):
        return self.tmdb.get_external_id_raw(external_id, source, language)

    def search_movie(self, title, year="unknown", language="hu-HU"):
        return self.tmdb.search_movie(title, year, language)

    def search_tv(self, title, year="unknown", language="hu-HU"):
        return self.tmdb.search_tv(title, year, language)

    def get_movie_details(self, movie_id, language="hu-HU"):
        return self.tmdb.get_movie_details(movie_id, language)

    def get_tv_show_details(self, tv_id, language="hu-HU", force_refresh=False):
        return self.tmdb.get_tv_details(tv_id, language, force_refresh)

    def get_from_tmdb_movie(self, title, year, language="hu-HU"):
        return self.tmdb.search_movie(title, year, language)

    def get_from_tmdb_movie_detail(self, id, language="hu-HU"):
        return self.tmdb.get_movie_details(id, language)

    def get_from_tmdb_tv(self, title, year, language="hu-HU"):
        return self.tmdb.search_tv(title, year, language)

    def get_from_tmdb_tv_external(self, id):
        return self.tmdb.get_tv_external_ids(id)

    def get_from_tmdb_tv_detail(self, id, language="hu-HU"):
        return self.tmdb.get_tv_details(id, language)

    def get_from_tmdb_episode(self, id, season_number, episode_number, language="hu-HU"):
        return self.tmdb.get_episode_details(id, season_number, episode_number, language)

    def get_from_tmdb_season(self, id, season_number, language="hu-HU", force_refresh=False):
        return self.tmdb.get_season_details(id, season_number, language, force_refresh)

    def get_from_tmdb(self, id, media_type, language="hu-HU", force_refresh=False):
        if media_type == 'movie':
            return self.tmdb.get_movie_details(id, language, force_refresh)
        elif media_type == 'tv':
            return self.tmdb.get_tv_details(id, language, force_refresh)
        return None
