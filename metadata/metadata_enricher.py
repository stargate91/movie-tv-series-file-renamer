import logging
from core.models import Movie, Episode, Ratings

logger = logging.getLogger(__name__)

def get_ratings_from_omdb(api_client, imdb_id):
    omdb_data = api_client.get_from_omdb_by_imdb_id(imdb_id)

    ratings = Ratings()

    for rating in omdb_data.get("Ratings", []):
        source = rating['Source']
        value = rating['Value']

        if source == "Internet Movie Database":
            try:
                ratings.imdb = float(value.split("/")[0])
            except (ValueError, IndexError):
                pass
        elif source == "Rotten Tomatoes":
            try:
                ratings.rotten_tomatoes = value.replace("%", "")
            except (ValueError, IndexError):
                pass
        elif source == "Metacritic":
            try:
                ratings.metacritic = value.split("/")[0]
            except (ValueError, IndexError):
                pass

    return ratings

def enricher(standardized_files, api_client):
    """Enrich Movie/Episode objects with ratings, genres, and episode details.
    
    Accepts and returns typed Movie/Episode objects (not dicts).
    """
    enriched_files = []
    unexpected_episodes = []

    for item in standardized_files:

        if isinstance(item, Movie):
            movie_data = api_client.get_from_tmdb_movie_detail(item.tmdb_id)
            imdb_id = movie_data.get('imdb_id', 'Unknown IMDb ID')
            genres_raw = movie_data.get('genres', 'Unknown Genres')
            genre_names = [genre["name"] for genre in genres_raw]

            item.genres = " ".join(genre_names)
            item.ratings = get_ratings_from_omdb(api_client, imdb_id)

            enriched_files.append(item)

        elif isinstance(item, Episode):
            series_data = api_client.get_from_tmdb_tv_detail(item.tmdb_id)
            item.series_status = series_data.get('status', 'unknown')
            last_air_date = series_data.get('last_air_date', 'Ongoing')
            if last_air_date != "Ongoing":
                item.last_air_year = last_air_date.split('-')[0]
            else:
                item.last_air_year = "Ongoing"
            item.last_air_date = last_air_date

            genres_raw = series_data.get('genres', 'Unknown Genres')
            genre_names = [genre["name"] for genre in genres_raw]
            item.genres = " ".join(genre_names)

            series_external_data = api_client.get_from_tmdb_tv_external(item.tmdb_id)
            imdb_id = series_external_data.get('imdb_id', 'Unknown IMDb ID')

            episode_data = api_client.get_from_tmdb_episode(
                item.tmdb_id, item.season_number, item.episode_number
            )

            if episode_data:
                item.episode_title = episode_data.get('name', 'Unknown Episode Title')
                item.season_number = episode_data.get('season_number', item.season_number)
                item.episode_number = episode_data.get('episode_number', item.episode_number)
                item.air_date = episode_data.get('air_date', 'Unknown Air Date')
                item.air_year = item.air_date.split('-')[0]
            else:
                unexpected_episodes.append(item)
                logger.warning(f"No episode found for {item.file_path}")

            item.ratings = get_ratings_from_omdb(api_client, imdb_id)

            enriched_files.append(item)

    return enriched_files, unexpected_episodes
