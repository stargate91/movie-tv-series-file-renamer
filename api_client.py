from cache import CacheHandler
import requests

class APIClient:
    def __init__(
        self,
        omdb_key,
        tmdb_key,
        tmdb_bearer_token,
        omdb_cache_file="omdb_cache.json",
        tmdb_movie_cache_file="tmdb_movie_cache.json",
        tmdb_movie_detail_cache_file="tmdb_movie_detail_cache.json",
        tmdb_tv_cache_file="tmdb_tv_cache.json",
        tmdb_tv_external_cache_file="tmdb_tv_external_cache.json",
        tmdb_tv_detail_cache_file="tmdb_tv_detail_cache.json",
        tmdb_episode_cache_file="tmdb_episode_cache.json"
    ):

        self.omdb_key = omdb_key
        self.tmdb_key = tmdb_key
        self.tmdb_bearer_token = tmdb_bearer_token
        self.omdb_cache = CacheHandler(omdb_cache_file)
        self.tmdb_movie_cache = CacheHandler(tmdb_movie_cache_file)
        self.tmdb_movie_detail_cache = CacheHandler(tmdb_movie_detail_cache_file)
        self.tmdb_tv_cache = CacheHandler(tmdb_tv_cache_file)
        self.tmdb_tv_external_cache = CacheHandler(tmdb_tv_external_cache_file)
        self.tmdb_tv_detail_cache = CacheHandler(tmdb_tv_detail_cache_file)
        self.tmdb_episode_cache = CacheHandler(tmdb_episode_cache_file)

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
        
        if year == "unknown":
            api_url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_key}&query={title}"
        else:
            api_url = f"https://api.themoviedb.org/3/search/tv?api_key={self.tmdb_key}&query={title}&year={year}"

        headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}"
        }        

        return self._get_from_api(api_url, cache_key, self.tmdb_tv_cache, headers)

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
