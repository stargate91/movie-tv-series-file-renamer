import requests
import logging
from core.exceptions import APIAuthError, NetworkConnectionError, AppError

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, omdb_key, tmdb_key, tmdb_bearer_token, db=None):
        self.omdb_key = omdb_key
        self.tmdb_key = tmdb_key
        self.tmdb_bearer_token = tmdb_bearer_token
        self.db = db # LibraryDB instance for caching
        self.session = requests.Session()

    def _get_from_api(self, api_url, cache_key, headers=None, params=None, required_keys=None):
        if self.db:
            cached_data = self.db.get_api_cache(cache_key)
            if cached_data:
                # Validate cache: if required_keys are missing, invalidate and re-fetch
                if required_keys and isinstance(cached_data, dict):
                    missing = [k for k in required_keys if k not in cached_data]
                    if missing:
                        logger.info(f"Cache stale (missing {missing}), re-fetching: {cache_key}")
                        self.db.delete_api_cache(cache_key)
                    else:
                        logger.debug(f"Cache hit: {cache_key}")
                        return cached_data
                else:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_data

        try:
            response = self.session.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code in (401, 403):
                raise APIAuthError(f"API Authentication failed (Status: {response.status_code}). Please check your API keys.")
                
            response.raise_for_status()

            data = response.json()
            if self.db:
                self.db.set_api_cache(cache_key, data)
            return data

        except APIAuthError:
            raise
        except requests.exceptions.ConnectionError as e:
            raise NetworkConnectionError(f"Failed to connect to API: {str(e)}")
        except requests.exceptions.Timeout:
            raise NetworkConnectionError(f"API request timed out for {cache_key}")
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {cache_key}: {str(e)}")
            raise AppError(f"API request failed for {cache_key}: {str(e)}")
        except ValueError as e:
            logger.error(f"API JSON parse failed for {cache_key}: {str(e)}")
            raise AppError(f"Invalid API response format for {cache_key}: {str(e)}")

    def get_from_omdb_by_imdb_id(self, imdb_id):
        cache_key = f"imdb-{imdb_id}"
        api_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={self.omdb_key}"
        return self._get_from_api(api_url, cache_key)

    def get_by_external_id(self, external_id, source="imdb_id", language="hu-HU"):
        """Finds TMDB content using external IDs like IMDB."""
        cache_key = f"find-{external_id}-{language}"
        api_url = f"https://api.themoviedb.org/3/find/{external_id}?api_key={self.tmdb_key}&external_source={source}&language={language}"
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers)

    def search_movie(self, title, year="unknown", language="hu-HU"):
        return self.get_from_tmdb_movie(title, year, language)

    def search_tv(self, title, year="unknown", language="hu-HU"):
        return self.get_from_tmdb_tv(title, year, language)

    def get_movie_details(self, movie_id, language="hu-HU"):
        return self.get_from_tmdb_movie_detail(movie_id, language)

    def get_tv_show_details(self, tv_id, language="hu-HU"):
        return self.get_from_tmdb_tv_detail(tv_id, language)

    def get_from_tmdb_movie(self, title, year, language="hu-HU"):
        cache_key = f"movie-{title}-{year}-{language}"
        api_url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": self.tmdb_key, "query": title, "language": language}
        if year and year != "unknown":
            params["year"] = year
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers, params=params)

    def get_from_tmdb_movie_detail(self, id, language="hu-HU"):
        cache_key = f"movie-detail-{id}-{language}"
        # append_to_response=credits to get Director and Cast
        api_url = f"https://api.themoviedb.org/3/movie/{id}?api_key={self.tmdb_key}&language={language}&append_to_response=credits"
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers, required_keys=['credits'])

    def get_from_tmdb_tv(self, title, year, language="hu-HU"):
        cache_key = f"tv-{title}-{year}-{language}"
        api_url = "https://api.themoviedb.org/3/search/tv"
        params = {"api_key": self.tmdb_key, "query": title, "language": language}
        if year and year != "unknown":
            params["first_air_date_year"] = year
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers, params=params)

    def get_from_tmdb_tv_external(self, id):
        cache_key = f"tv-external-{id}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}/external_ids?api_key={self.tmdb_key}"
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers)

    def get_from_tmdb_tv_detail(self, id, language="hu-HU"):
        cache_key = f"tv-detail-{id}-{language}"
        # append_to_response=credits,external_ids to get Cast/Crew and IMDb ID
        api_url = f"https://api.themoviedb.org/3/tv/{id}?api_key={self.tmdb_key}&language={language}&append_to_response=credits,external_ids"
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers, required_keys=['credits', 'external_ids'])

    def get_from_tmdb_episode(self, id, season_number, episode_number, language="hu-HU"):
        s_num = season_number[0] if isinstance(season_number, list) else season_number
        e_num = episode_number[0] if isinstance(episode_number, list) else episode_number
        cache_key = f"episode-{id}-{s_num}-{e_num}-{language}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}/season/{s_num}/episode/{e_num}?api_key={self.tmdb_key}&language={language}&append_to_response=external_ids"
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers, required_keys=['external_ids'])

    def get_from_tmdb_season(self, id, season_number, language="hu-HU"):
        cache_key = f"season-{id}-{season_number}-{language}"
        api_url = f"https://api.themoviedb.org/3/tv/{id}/season/{season_number}?api_key={self.tmdb_key}&language={language}&append_to_response=external_ids"
        headers = {"Authorization": f"Bearer {self.tmdb_bearer_token}"}
        return self._get_from_api(api_url, cache_key, headers, required_keys=['episodes'])

    def get_from_tmdb(self, id, media_type, language="hu-HU"):
        """Unified helper to get movie or TV show details."""
        if media_type == 'movie':
            return self.get_from_tmdb_movie_detail(id, language)
        elif media_type == 'tv':
            return self.get_from_tmdb_tv_detail(id, language)
        return None
