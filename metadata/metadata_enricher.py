import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.models import Movie, Episode, Ratings
from metadata.video_metadata import get_video_metadata

logger = logging.getLogger(__name__)

def get_ratings_from_omdb(api_client, imdb_id):
    omdb_data = api_client.get_from_omdb_by_imdb_id(imdb_id)
    ratings = Ratings()
    for rating in omdb_data.get("Ratings", []):
        source = rating['Source']
        value = rating['Value']
        if source == "Internet Movie Database":
            try: ratings.imdb = float(value.split("/")[0])
            except: pass
        elif source == "Rotten Tomatoes":
            try: ratings.rotten_tomatoes = value.replace("%", "")
            except: pass
        elif source == "Metacritic":
            try: ratings.metacritic = value.split("/")[0]
            except: pass
    return ratings

def enricher(standardized_files, api_client, ui=None, language="hu-HU", fallback_language="en-US", force_tech=False, templates=None, discovery_data=None):
    tech_needed = force_tech
    discovery_data = discovery_data or {}
    if not tech_needed and templates:
        tech_tags = ["resolution", "video_codec", "video_bitrate", "framerate", "hdr_type", "bit_depth", 
                     "audio_codec", "audio_channels", "audio_channels_description", "first_audio_channel_language", 
                     "audio_streams_count", "subtitle_languages"]
        for tmpl in templates:
            if tmpl and any(f"{{{tag}}}" in tmpl for tag in tech_tags):
                tech_needed = True
                break

    enriched_files = []
    unexpected_episodes = []
    total = len(standardized_files)
    processed_count = 0
    progress_lock = threading.Lock()

    def process_item(item):
        nonlocal processed_count
        try:
            # 1. Use Discovery Data for Technical Specs (MediaInfo)
            disc = discovery_data.get(str(item.file_path), {})
            tech = disc.get('technical', {})
            
            if tech_needed:
                if tech:
                    # Map discovery technical to item.tech_metadata dict
                    item.tech_metadata = {
                        'resolution': tech.get('resolution'),
                        'video_codec': tech.get('vcodec'),
                        'audio_codec': tech.get('acodec'),
                        'audio_channels': tech.get('channels'),
                        'subtitle_languages': ", ".join(tech.get('subs', [])) if isinstance(tech.get('subs'), list) else tech.get('subs')
                    }
                else:
                    item.tech_metadata = get_video_metadata(str(item.file_path))

            # 2. Use Discovery IDs for OMDB lookup
            target_imdb = disc.get('imdb_id') or (item.imdb_id if hasattr(item, 'imdb_id') else None)
            if target_imdb:
                item.ratings = get_ratings_from_omdb(api_client, target_imdb)

            if isinstance(item, Movie):
                movie_data = api_client.get_from_tmdb_movie_detail(item.tmdb_id, language=language)
                if not isinstance(movie_data, dict): movie_data = {}
                orig_title = movie_data.get('original_title')
                curr_title = movie_data.get('title')
                orig_lang = movie_data.get('original_language')
                if fallback_language and curr_title == orig_title and orig_lang != language.split('-')[0]:
                    fb_data = api_client.get_from_tmdb_movie_detail(item.tmdb_id, language=fallback_language)
                    if isinstance(fb_data, dict) and fb_data.get('title'): movie_data = fb_data
                
                imdb_id = movie_data.get('imdb_id', 'Unknown IMDb ID')
                genres_raw = movie_data.get('genres', 'Unknown Genres')
                genre_names = [genre["name"] for genre in genres_raw] if isinstance(genres_raw, list) else []
                item.genres = " ".join(genre_names)
                item.ratings = get_ratings_from_omdb(api_client, imdb_id)
                
            elif isinstance(item, Episode):
                series_data = api_client.get_from_tmdb_tv_detail(item.tmdb_id, language=language)
                if not isinstance(series_data, dict): series_data = {}
                orig_name = series_data.get('original_name')
                curr_name = series_data.get('name')
                orig_lang = series_data.get('original_language')
                if fallback_language and curr_name == orig_name and orig_lang != language.split('-')[0]:
                    fb_data = api_client.get_from_tmdb_tv_detail(item.tmdb_id, language=fallback_language)
                    if isinstance(fb_data, dict) and fb_data.get('name'): series_data = fb_data

                item.series_title = series_data.get('name', item.series_title)
                item.series_status = series_data.get('status', 'unknown')
                last_air_date = series_data.get('last_air_date', 'Ongoing')
                item.last_air_year = last_air_date.split('-')[0] if last_air_date and "-" in last_air_date else "Ongoing"
                item.last_air_date = last_air_date
                
                genres_raw = series_data.get('genres', 'Unknown Genres')
                genre_names = [genre["name"] for genre in genres_raw] if isinstance(genres_raw, list) else []
                item.genres = " ".join(genre_names)
                
                series_external_data = api_client.get_from_tmdb_tv_external(item.tmdb_id)
                if not isinstance(series_external_data, dict): series_external_data = {}
                imdb_id = series_external_data.get('imdb_id', 'Unknown IMDb ID')
                episode_data = api_client.get_from_tmdb_episode(item.tmdb_id, item.season_number, item.episode_number, language=language)
                if not isinstance(episode_data, dict): episode_data = {}
                
                if episode_data and fallback_language:
                    if not episode_data.get('name') or episode_data.get('name') == f"Episode {item.episode_number}":
                        fb_ep_data = api_client.get_from_tmdb_episode(item.tmdb_id, item.season_number, item.episode_number, language=fallback_language)
                        if isinstance(fb_ep_data, dict) and fb_ep_data.get('name'): episode_data = fb_ep_data

                if episode_data:
                    item.episode_title = episode_data.get('name', 'Unknown Episode Title')
                    item.air_date = episode_data.get('air_date', 'Unknown Air Date')
                    item.air_year = item.air_date.split('-')[0] if '-' in item.air_date else item.air_date
                
                item.ratings = get_ratings_from_omdb(api_client, imdb_id)

            with progress_lock:
                processed_count += 1
                if ui: ui.update_progress(processed_count, total, f"Status: Enriching {processed_count}/{total}")
            return item
        except Exception as e:
            logger.error(f"Error enriching {item.file_path}: {e}")
            # Attach error info but still return the item so it doesn't get lost
            item.enrichment_error = str(e)
            item.status = 'no_match' # Force it back to no_match so user can fix the broken ID
            with progress_lock: processed_count += 1
            return item

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_item, it) for it in standardized_files]
        for future in as_completed(futures):
            res = future.result()
            if res: enriched_files.append(res)

    return enriched_files, unexpected_episodes
