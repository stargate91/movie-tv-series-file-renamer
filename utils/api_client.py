from utils.cache import DataStore
import requests
import logging
from core.exceptions import APIAuthError, NetworkConnectionError, AppError

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(
        self,
        omdb_key,
        tmdb_key,
        tmdb_bearer_token,
        omdb_cache_file="omdb_cache",
        tmdb_movie_cache_file="tmdb_movie_cache",
        tmdb_movie_detail_cache_file="tmdb_movie_detail_cache",
        tmdb_tv_cache_file="tmdb_tv_cache",
        tmdb_tv_external_cache_file="tmdb_tv_external_cache",
        tmdb_tv_detail_cache_file="tmdb_tv_detail_cache",
        tmdb_episode_cache_file="tmdb_episode_cache",
        tmdb_season_cache_file="tmdb_season_cache"
    ):

        self.omdb_key = omdb_key
        self.tmdb_key = tmdb_key
        self.tmdb_bearer_token = tmdb_bearer_token
        self.omdb_cache = DataStore(omdb_cache_file)
        self.tmdb_movie_cache = DataStore(tmdb_movie_cache_file)
        self.tmdb_movie_detail_cache = DataStore(tmdb_movie_detail_cache_file)
        self.tmdb_tv_cache = DataStore(tmdb_tv_cache_file)
        self.tmdb_tv_external_cache = DataStore(tmdb_tv_external_cache_file)
        self.tmdb_tv_detail_cache = DataStore(tmdb_tv_detail_cache_file)
        self.tmdb_episode_cache = DataStore(tmdb_episode_cache_file)
        self.tmdb_season_cache = DataStore(tmdb_season_cache_file)

    def _get_from_api(self, api_url, cache_key, cache_handler, headers=None):

        cached_data = cache_handler.get(cache_key)
        if cached_data:
            logger.debug(f"Cache hit: {cache_key}")
            return cached_data

        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code in (401, 403):
                raise APIAuthError(f"API Authentication failed (Status: {response.status_code}). Please check your API keys.")
                
            response.raise_for_status()

            data = response.json()
            cache_handler.set(cache_key, data)
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
        
        return self._get_from_api(api_url, cache_key, self.omdb_cache)

    def get_from_tmdb_movie(self, title, year):
        cache_key = f"movie-{title}-{year}"
        if year == "unknown":
            api_url = f"https://api.themoviedb.org/3/search/movie?api_key={self.tmdb_key}&query={title}"
        else:
            api_url = f"https://api.themoviedb.org/3/search/movie?api_key={self.tmdb_key}&query={title}&year={year}"
        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }

        return self._get_from_api(api_url, cache_key, self.tmdb_movie_cache, headers)

    def get_from_tmdb_movie_detail(self, id):
        cache_key = f"movie-detail-{id}"

        api_url = f"https://api.themoviedb.org/3/movie/{id}?api_key={self.tmdb_key}"

        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }
        
        return self._get_from_api(api_url, cache_key, self.tmdb_movie_cache, headers)
    
    def get_from_tmdb_tv(self, title, year):
        cache_key = f"series-{title}-{year}"
        
        if not year or year == "unknown":
            api_url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_key}&query={title}"
        else:
            api_url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_key}&query={title}&first_air_date_year={year}"

        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }        

        return self._get_from_api(api_url, cache_key, self.tmdb_tv_cache, headers)

    def get_tv_episode_details(self, tv_id, season, episode):
        """Fetch details for a specific episode."""
        cache_key = f"episode-detail-{tv_id}-{season}-{episode}"
        api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season}/episode/{episode}?api_key={self.tmdb_key}"
        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }
        return self._get_from_api(api_url, cache_key, self.tmdb_episode_cache, headers)

    def get_tv_season_details(self, tv_id, season):
        """Fetch details for a specific season."""
        cache_key = f"season-detail-{tv_id}-{season}"
        api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season}?api_key={self.tmdb_key}"
        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }
        return self._get_from_api(api_url, cache_key, self.tmdb_season_cache, headers)

    def get_from_tmdb_tv_detail(self, id):
        cache_key = f"series-detail-{id}"
        
        api_url = f"https://api.themoviedb.org/3/tv/{id}?api_key={self.tmdb_key}"

        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }        

        return self._get_from_api(api_url, cache_key, self.tmdb_tv_detail_cache, headers)

    def get_from_tmdb_tv_external(self, id):
        cache_key = f"series-external-{id}"
        
        api_url = f"https://api.themoviedb.org/3/tv/{id}/external_ids?api_key={self.tmdb_key}"

        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }

        return self._get_from_api(api_url, cache_key, self.tmdb_tv_external_cache, headers)

    def get_from_tmdb_episode(self, id, season, episode):
        cache_key = f"episode_detail-{id}-S{season}E{episode}"
        
        api_url = f"https://api.themoviedb.org/3/tv/{id}/season/{season}/episode/{episode}?api_key={self.tmdb_key}"

        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }

        return self._get_from_api(api_url, cache_key, self.tmdb_episode_cache, headers)
