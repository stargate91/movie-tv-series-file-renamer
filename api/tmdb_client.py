import json
from api.base_client import BaseClient
from api.base_provider import BaseMediaProvider, ProviderResult
from typing import List, Optional

class TMDBClient(BaseClient, BaseMediaProvider):
    """
    Client for The Movie Database (TMDB) API.
    """
    def __init__(self, api_key, bearer_token, db=None):
        super().__init__(db=db, min_interval=0.1) # 10 requests per second
        self.api_key = str(api_key).strip(' "\'') if api_key else ""
        self.bearer_token = str(bearer_token).strip(' "\'') if bearer_token else ""
        # If we have a bearer token, we should use it for all requests via headers.
        # TMDB allows using either api_key (v3) in query OR Bearer token (v4) in header.
        self.headers = {"Authorization": f"Bearer {self.bearer_token}"} if self.bearer_token else {}

    def get_external_id_raw(self, external_id, source="imdb_id", language="hu-HU"):
        cache_key = f"find-{external_id}-{language}"
        api_url = f"https://api.themoviedb.org/3/find/{external_id}?api_key={self.api_key}&external_source={source}&language={language}"
        return self._get_from_api(api_url, cache_key, self.headers)

    def search_movie(self, title, year="unknown", language="hu-HU"):
        cache_key = f"movie-{title}-{year}-{language}"
        api_url = "https://api.themoviedb.org/3/search/movie"
        # Always include api_key if available, as it's the most stable for v3 endpoints
        params = {"query": title.strip(), "language": language}
        if self.api_key:
            params["api_key"] = self.api_key
            
        if year and year != "unknown":
            params["year"] = year
        return self._get_from_api(api_url, cache_key, self.headers, params=params)

    def search_tv(self, title, year="unknown", language="hu-HU"):
        cache_key = f"tv-{title}-{year}-{language}"
        api_url = "https://api.themoviedb.org/3/search/tv"
        params = {"query": title.strip(), "language": language}
        if self.api_key:
            params["api_key"] = self.api_key
            
        if year and year != "unknown":
            params["first_air_date_year"] = year
        return self._get_from_api(api_url, cache_key, self.headers, params=params)

    def get_movie_details(self, id, language="hu-HU"):
        cache_key = f"movie-detail-{id}-{language}"
        api_url = f"https://api.themoviedb.org/3/movie/{id}?api_key={self.api_key}&language={language}&append_to_response=credits"
        return self._get_from_api(api_url, cache_key, self.headers, required_keys=['credits'])

    def get_tv_details(self, id, language="hu-HU"):
        cache_key = f"tv-detail-{id}-{language}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}?api_key={self.api_key}&language={language}&append_to_response=credits,external_ids"
        return self._get_from_api(api_url, cache_key, self.headers, required_keys=['credits', 'external_ids'])

    def get_season_details(self, id, season_number, language="hu-HU"):
        cache_key = f"season-{id}-{season_number}-{language}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}/season/{season_number}?api_key={self.api_key}&language={language}&append_to_response=external_ids"
        return self._get_from_api(api_url, cache_key, self.headers, required_keys=['episodes'])

    def get_episode_details(self, id, season_number, episode_number, language="hu-HU"):
        cache_key = f"episode-{id}-{season_number}-{episode_number}-{language}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}/season/{season_number}/episode/{episode_number}?api_key={self.api_key}&language={language}&append_to_response=external_ids"
        return self._get_from_api(api_url, cache_key, self.headers, required_keys=['external_ids'])

    def get_tv_external_ids(self, id):
        cache_key = f"tv-external-{id}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}/external_ids?api_key={self.api_key}"
        return self._get_from_api(api_url, cache_key, self.headers)

    def get_full_details(self, id, media_type, language="hu-HU"):
        if media_type == 'movie':
            return self.get_movie_details(id, language)
        elif media_type == 'tv':
            return self.get_tv_details(id, language)
        return None

    # --- BaseMediaProvider Implementation ---
    def search(self, query: str, year: Optional[str] = None, media_type: str = "movie", language: str = "en-US") -> List[ProviderResult]:
        if media_type == 'movie':
            raw = self.search_movie(query, year, language)
        else:
            raw = self.search_tv(query, year, language)
        
        results = []
        for item in raw.get('results', []):
            results.append(ProviderResult(
                tmdb_id=str(item.get('id')),
                title=item.get('title') or item.get('name', 'Unknown'),
                year=(item.get('release_date') or item.get('first_air_date', ''))[:4],
                media_type=media_type,
                poster_path=item.get('poster_path'),
                overview=item.get('overview'),
                rating=item.get('vote_average')
            ))
        return results

    def get_details(self, media_id: str, media_type: str = "movie", language: str = "en-US") -> Optional[ProviderResult]:
        raw = self.get_full_details(media_id, media_type, language)
        if not raw: return None
        
        networks = None
        if raw.get('networks'):
            networks = ", ".join([n['name'] for n in raw['networks']])
        
        collection = None
        if raw.get('belongs_to_collection'):
            collection = raw['belongs_to_collection'].get('name')
            
        return ProviderResult(
            tmdb_id=str(raw.get('id')),
            imdb_id=raw.get('imdb_id') or raw.get('external_ids', {}).get('imdb_id'),
            title=raw.get('title') or raw.get('name', 'Unknown'),
            year=(raw.get('release_date') or raw.get('first_air_date', ''))[:4],
            media_type=media_type,
            poster_path=raw.get('poster_path'),
            overview=raw.get('overview'),
            rating=raw.get('vote_average'),
            networks=networks,
            collection=collection
        )

    def get_by_external_id(self, external_id: str, source: str = "imdb_id", language: str = "en-US") -> Optional[ProviderResult]:
        raw = self.get_external_id_raw(external_id, source, language)
        # TMDB /find returns { 'movie_results': [], 'tv_results': [], ... }
        for m_type in ['movie_results', 'tv_results', 'person_results']:
            if raw.get(m_type):
                item = raw[m_type][0]
                media_type = 'movie' if m_type == 'movie_results' else 'tv'
                return ProviderResult(
                    tmdb_id=str(item.get('id')),
                    imdb_id=external_id if source == 'imdb_id' else None,
                    title=item.get('title') or item.get('name'),
                    year=(item.get('release_date') or item.get('first_air_date', ''))[:4],
                    media_type=media_type,
                    poster_path=item.get('poster_path')
                )
        return None
