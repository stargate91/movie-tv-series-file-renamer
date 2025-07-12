from cache import CacheHandler
import requests

class APIClient:
    def __init__(self, omdb_key, tmdb_key, tmdb_bearer_token, omdb_cache_file="omdb_cache.json", tmdb_movie_cache_file="tmdb_movie_cache.json", tmdb_tv_cache_file="tmdb_tv_cache.json"):
        self.omdb_key = omdb_key
        self.tmdb_key = tmdb_key
        self.tmdb_bearer_token = tmdb_bearer_token
        self.omdb_cache = CacheHandler(omdb_cache_file)
        self.tmdb_movie_cache = CacheHandler(tmdb_movie_cache_file)
        self.tmdb_tv_cache = CacheHandler(tmdb_tv_cache_file)

    def _get_from_api(self, api_url, cache_key, cache_handler, headers=None):

        cached_data = cache_handler.get(cache_key)
        if cached_data:
            print(f"Cache hit: {cache_key}")
            return cached_data

        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            cache_handler.set(cache_key, data)
            return data

        except requests.exceptions.RequestException as e:
            print(f"API request failed for {cache_key}: {str(e)}")
            return None

        except ValueError as e:
            print(f"API request failed for {cache_key}: {str(e)}")
            return None

    def get_from_omdb(self, title, year):
        cache_key = f"{title}-{year}"
        if year == "Unknown Year":
            api_url = f"http://www.omdbapi.com/?t={title}&apikey={self.omdb_key}&"
        else:
            api_url = f"http://www.omdbapi.com/?t={title}&y={year}&apikey={self.omdb_key}"
        
        return self._get_from_api(api_url, cache_key, self.omdb_cache)

    def get_from_tmdb_movie(self, title, year):
        cache_key = f"{title}-{year}"
        if year == "Unknown Year":
            api_url = f"https://api.themoviedb.org/3/search/movie?api_key={self.tmdb_key}&query={title}"
        else:
            api_url = f"https://api.themoviedb.org/3/search/movie?api_key={self.tmdb_key}&query={title}&year={year}"
        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }

        return self._get_from_api(api_url, cache_key, self.tmdb_movie_cache, headers)
    
    def get_from_tmdb_tv(self, title, year):
        cache_key = f"{title}-{year}"
        if year == "Unknown Year":
            api_url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_key}&query={title}"
        else:
            api_url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_key}&query={title}&year={year}"

        return self._get_from_api(api_url, cache_key, self.tmdb_tv_cache)
