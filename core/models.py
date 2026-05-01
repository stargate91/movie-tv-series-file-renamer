from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ExtraMetadata:
    """Metadata parsed from filename/foldername by guessit (release group, source, etc.)."""
    release_group: str = "Unknown Release Group"
    source: str = "Unknown Source"
    other: str = "Unknown"
    edition: str = "Unknown Edition"
    streaming_service: str = "Unknown Streaming Service"

    @classmethod
    def from_dict(cls, data: dict) -> "ExtraMetadata":
        return cls(
            release_group=data.get('release_group', cls.release_group),
            source=data.get('source', cls.source),
            other=data.get('other', cls.other),
            edition=data.get('edition', cls.edition),
            streaming_service=data.get('streaming_service', cls.streaming_service),
        )


@dataclass
class Ratings:
    """Aggregated ratings from OMDB (IMDb, Rotten Tomatoes, Metacritic)."""
    imdb: Any = "Unknown IMDb Rating"
    rotten_tomatoes: str = "Unknown Rotten Tomatoes Rating"
    metacritic: str = "Unknown Metacritic Rating"


@dataclass
class Movie:
    """A fully resolved movie with all metadata needed for renaming."""
    file_path: str
    title: str = "Unknown Title"
    release_date: str = "Unknown Release Date"
    year: str = "Unknown Year"
    tmdb_id: Any = "Unknown ID"
    extras: ExtraMetadata = field(default_factory=ExtraMetadata)
    tech_metadata: Dict[str, Any] = field(default_factory=dict)
    genres: str = "Unknown Genres"
    ratings: Ratings = field(default_factory=Ratings)
    poster_path: Optional[str] = None
    associated_samples: list[str] = field(default_factory=list)
    part: str = "" # CD1, CD2, Part 1, etc.

    @property
    def file_type(self) -> str:
        return "movie"

    def to_template_dict(self) -> dict:
        """Returns a flat dict suitable for str.format() in rename templates."""
        d = {
            "movie_title": self.title,
            "movie_release_date": self.release_date,
            "movie_year": self.year,
            "genres": self.genres,
            "imdb_rating": self.ratings.imdb,
            "rotten_rating": self.ratings.rotten_tomatoes,
            "metacritic_rating": self.ratings.metacritic,
            "release_group": self.extras.release_group,
            "source": self.extras.source,
            "other": self.extras.other,
            "edition": self.extras.edition,
            "streaming_service": self.extras.streaming_service,
            "part": f" - {self.part}" if self.part else ""
        }
        # Add technical metadata
        if self.tech_metadata:
            d.update(self.tech_metadata)
        return d


@dataclass
class Episode:
    """A fully resolved TV episode with all metadata needed for renaming."""
    file_path: str
    series_title: str = "Unknown Title"
    episode_title: str = "Unknown Episode Title"
    season_number: Any = "unknown"
    episode_number: Any = "unknown"
    first_air_date: str = "Unknown First Air Date"
    first_air_year: str = "Unknown First Air Year"
    last_air_date: str = "unknown"
    last_air_year: str = "unknown"
    air_date: str = "unknown"
    air_year: str = "unknown"
    series_status: str = "unknown"
    tmdb_id: Any = "Unknown ID"
    extras: ExtraMetadata = field(default_factory=ExtraMetadata)
    tech_metadata: Dict[str, Any] = field(default_factory=dict)
    genres: str = "Unknown Genres"
    ratings: Ratings = field(default_factory=Ratings)
    poster_path: Optional[str] = None
    series_poster_path: Optional[str] = None
    season_poster_path: Optional[str] = None
    associated_samples: list[str] = field(default_factory=list)
    part: str = ""

    @property
    def file_type(self) -> str:
        return "episode"

    def to_template_dict(self, season_str: str, episode_str: str) -> dict:
        """Returns a flat dict suitable for str.format() in rename templates."""
        d = {
            "series_title": self.series_title,
            "episode_title": self.episode_title,
            "season_number": season_str,
            "episode_number": episode_str,
            "first_air_date": self.first_air_date,
            "first_air_year": self.first_air_year,
            "last_air_date": self.last_air_date,
            "last_air_year": self.last_air_year,
            "air_date": self.air_date,
            "air_year": self.air_year,
            "status": self.series_status,
            "genres": self.genres,
            "imdb_rating": self.ratings.imdb,
            "rotten_rating": self.ratings.rotten_tomatoes,
            "metacritic_rating": self.ratings.metacritic,
            "release_group": self.extras.release_group,
            "source": self.extras.source,
            "other": self.extras.other,
            "edition": self.extras.edition,
            "streaming_service": self.extras.streaming_service,
            "part": f" - {self.part}" if self.part else ""
        }
        # Add technical metadata
        if self.tech_metadata:
            d.update(self.tech_metadata)
        return d


@dataclass
class RenamingTask:
    """Result of a single file rename operation."""
    old_path: str
    new_filename: str
    new_path: str
    status: str = "pending"  # pending, success, dry_run, error
    error_message: Optional[str] = None
