import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)



def group_by_folders(episodes):
    folders = {}
    main_folders = {}

    for file_data in episodes:
        file_path = file_data['file_path']
        directory = os.path.dirname(file_path)
        main_directory = os.path.dirname(directory)

        if directory not in folders:
            folders[directory] = []
        folders[directory].append(file_data)

        if main_directory not in main_folders:
            main_folders[main_directory] = []
            
        if file_data not in main_folders[main_directory]:
            main_folders[main_directory].append(file_data)

    return folders, main_folders

def build_entry(item, selected):
    entry = {
        'file_path': item['file_path'],
        'file_type': item['file_type'],
        'extras': item['extras'],
        'details': selected
    }

    for key in ('season_file', 'episode_file', 'season_folder', 'episode_folder'):
        if key in item:
            entry[key] = item[key]

    return entry

def get_api_func(api_client, source):
    return {
        'tmdb': api_client.get_from_tmdb_movie,
        'tmdb_tv': api_client.get_from_tmdb_tv
    }.get(source)


def extract_results(result):
    return result.get('results', []) if result else []

def search_api(api_client, source, title, year):
    from core.exceptions import AppError
    try:
        api_func = get_api_func(api_client, source)
        if not api_func:
            raise AppError(f"Unsupported API source: {source}")
        result = api_func(title, year)
        results = extract_results(result)
        return result, results
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during API search: {e}", exc_info=True)
        raise AppError(f"Unexpected error during API search for '{title}': {str(e)}")


