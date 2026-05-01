import logging
from core.models import Movie, Episode, ExtraMetadata

logger = logging.getLogger(__name__)

def standardize_season_episode_numbers(file_data):
    season = file_data.get('season_file') or file_data.get('season_folder') or 'unknown'
    episode = file_data.get('episode_file') or file_data.get('episode_folder') or 'unknown'

    if season == 'unknown':
        logger.warning(f"Missing season number for file data: {file_data}")
    if episode == 'unknown':
        logger.warning(f"Missing episode number for file data: {file_data}")

    return season, episode

def standardize_metadata(handled_results):
    """Convert raw handler dicts into Movie/Episode dataclass objects.
    
    This is the dict → object boundary in the pipeline.
    Everything downstream works with typed objects.
    """
    if not handled_results:
        logger.info("There's nothing to standardize - no movies or episodes had a single match.")
        return [], []

    standardized_files = []
    unexpected_files = []

    for file_data in handled_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']
        extras = ExtraMetadata.from_dict(file_data.get('extras', {}))
        data = file_data['details']

        if file_type == "movie":
            title = data.get('title', 'Unknown Title')
            release_date = data.get('release_date', 'Unknown Release Date')
            if release_date != 'Unknown Release Date':
                year = release_date.split('-')[0]
            else:
                year = 'Unknown Year'

            tmdb_id = data.get('id', 'Unknown ID')

            standardized_files.append(Movie(
                file_path=file_path,
                title=title,
                release_date=release_date,
                year=year,
                tmdb_id=tmdb_id,
                extras=extras,
                poster_path=data.get('poster_path'),
                part=file_data.get('part', "")
            ))

        if file_type == "episode":
            series_title = data.get('series_name') or data.get('name') or 'Unknown Series'
            episode_title = data.get('name') if data.get('series_name') else 'Unknown Episode'
            
            first_air_date = data.get('first_air_date', 'Unknown First Air Date')
            if first_air_date != "Unknown First Air Date":
                first_air_year = first_air_date.split('-')[0]
            else:
                first_air_year = 'Unknown First Air Year'
                
            tmdb_id = data.get('series_id') or data.get('id', 'Unknown ID')
            season_number, episode_number = standardize_season_episode_numbers(file_data)

            if 'unknown' in [season_number, episode_number]:
                logger.warning(f"Unexpected files for {file_data['file_path']}.")
                unexpected_files.append(file_data)

            standardized_files.append(Episode(
                file_path=file_path,
                series_title=series_title,
                episode_title=episode_title,
                season_number=season_number,
                episode_number=episode_number,
                first_air_date=first_air_date,
                first_air_year=first_air_year,
                air_date=data.get('air_date', 'unknown'),
                air_year=data.get('air_date', '')[:4] if data.get('air_date') else 'unknown',
                tmdb_id=tmdb_id,
                extras=extras,
                poster_path=data.get('still_path') or data.get('poster_path'),
                series_poster_path=data.get('series_poster_path'),
                season_poster_path=data.get('season_poster_path'),
                part=file_data.get('part', "")
            ))

    return standardized_files, unexpected_files
