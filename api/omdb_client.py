from api.base_client import BaseClient
from api.base_provider import BaseMediaProvider, ProviderResult
from typing import List, Optional

class OMDBClient(BaseClient, BaseMediaProvider):
    """
    Client for OMDB API (primarily used for IMDb ratings).
    """
    def __init__(self, api_key, db=None):
        super().__init__(db=db, min_interval=0.5) # Throttled slightly more
        self.api_key = api_key

    def get_by_imdb_id(self, imdb_id):
        if not imdb_id: return None
        key = self.api_key
        if not key or "your_omdb_key" in key:
            return None
            
        cache_key = f"imdb-{imdb_id}"
        api_url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={key}"
        raw = self._get_from_api(api_url, cache_key)
        
        if raw and raw.get("Response") == "False":
            error_msg = raw.get("Error", "")
            if "limit reached" in error_msg.lower():
                from core.exceptions import APILimitReachedError
                raise APILimitReachedError("OMDb API daily limit reached (1000 requests). Try again tomorrow or use a different key.")
        
        return raw

    # --- BaseMediaProvider Implementation ---
    def search(self, query: str, year: Optional[str] = None, media_type: str = "movie", language: str = "en-US") -> List[ProviderResult]:
        # OMDb search uses 's' parameter
        cache_key = f"omdb-search-{query}-{year}"
        params = {"s": query, "apikey": self.api_key}
        if year: params["y"] = year
        if media_type == "tv": params["type"] = "series"
        
        raw = self._get_from_api("https://www.omdbapi.com/", cache_key, params=params)
        results = []
        if raw and raw.get("Response") == "True":
            for item in raw.get("Search", []):
                results.append(ProviderResult(
                    imdb_id=item.get("imdbID"),
                    title=item.get("Title"),
                    year=item.get("Year"),
                    media_type="tv" if item.get("Type") == "series" else "movie",
                    poster_path=item.get("Poster") if item.get("Poster") != "N/A" else None
                ))
        return results

    def get_details(self, media_id: str, media_type: str = "movie", language: str = "en-US") -> Optional[ProviderResult]:
        # media_id here is assumed to be IMDb ID for OMDB
        raw = self.get_by_imdb_id(media_id)
        if not raw or raw.get("Response") == "False": return None
        
        return ProviderResult(
            imdb_id=raw.get("imdbID"),
            title=raw.get("Title"),
            year=raw.get("Year"),
            media_type="tv" if raw.get("Type") == "series" else "movie",
            poster_path=raw.get("Poster") if raw.get("Poster") != "N/A" else None,
            overview=raw.get("Plot"),
            rating=float(raw.get("imdbRating")) if raw.get("imdbRating") != "N/A" else None
        )

    def get_by_external_id(self, external_id: str, source: str = "imdb_id", language: str = "en-US") -> Optional[ProviderResult]:
        if source == "imdb_id":
            return self.get_details(external_id, language=language)
        return None
