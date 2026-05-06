from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ProviderResult:
    """Unified media metadata result across different providers."""
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    title: str = ""
    year: Optional[str] = None
    media_type: str = "movie" # 'movie' or 'tv'
    poster_path: Optional[str] = None
    overview: Optional[str] = None
    rating: Optional[float] = None
    vote_count: Optional[int] = None
    networks: Optional[str] = None
    collection: Optional[str] = None
    
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}

class BaseMediaProvider(ABC):
    """
    Abstract base class for media metadata providers (TMDB, OMDB, etc.).
    Ensures a consistent interface for the engine.
    """
    
    @abstractmethod
    def search(self, query: str, year: Optional[str] = None, media_type: str = "movie", language: str = "en-US") -> List[ProviderResult]:
        """Search for movies or TV shows."""
        pass

    @abstractmethod
    def get_details(self, media_id: str, media_type: str = "movie", language: str = "en-US") -> Optional[ProviderResult]:
        """Get full details for a specific media item."""
        pass

    @abstractmethod
    def get_by_external_id(self, external_id: str, source: str = "imdb_id", language: str = "en-US") -> Optional[ProviderResult]:
        """Find media by external ID (e.g. IMDb ID)."""
        pass
