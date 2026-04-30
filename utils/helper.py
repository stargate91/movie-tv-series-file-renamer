import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LABELS = {
    "start":           ("🚀 ", ""),
    "live_mode":       ("⚠️ ", ""),
    "dry_run":         ("📝 ", ""),
    "name":            ("🎥 ", ""),
    "version":         ("📦 ", ""),
    "config":          ("⚙️ ", ""),
    "dir":             ("📁 ", ""),
    "up":              ("⚡ ", ""),
    "summary":         ("📋 ", ""),
    "skipped":         ("⏭️ ", ""),
    "unprocessed":     ("⏳ ", ""),
    "no_se_ep":        ("⚠️ ", ""),
    "unexpected_ep":   ("❓ ", ""),
    "renamed":         ("✅ ", ""),
    "done":            ("🎉 ", ""),
    "paper":           ("🧾 ", "")
}

def get_label(name, use_emojis):
    pair = LABELS.get(name, ("", ""))
    return pair[0] if use_emojis else pair[1]

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

def has_results(result):
    return result.get("total_results", 0) > 0 if result else False

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

def save_skipped_to_file(skipped):
    from utils.cache import DataStore
    store = DataStore("skipped")
    store.set("latest", skipped)
    logger.info("Skipped list saved to DataStore.")

def load_skipped_menu(ui, max_examples=2):
    from utils.cache import DataStore
    store = DataStore("skipped")
    skipped_files = store.get("latest")
    
    if not skipped_files:
        logger.info("No skipped data found.")
        return None

    ui.show_message(f"Found saved skipped files ({len(skipped_files)} entries)")

    ui.show_message("Examples:")
    for entry in skipped_files[:max_examples]:
        ui.show_message(f"- {entry.get('file_path', 'Unknown file')}")

    choice = ui.ask_decision(
        "[1] Resume from this\n[2] Ignore and start fresh\n[0] Exit",
        ["1", "2", "0"]
    )

    if choice == "1":
        return skipped_files
    elif choice == "2":
        logger.info("Ignoring the saved skipped files.")
        return None
    elif choice == "0":
        logger.info("Exiting.")
        exit(0)

def save_rename_history_to_file(rename_history):
    from utils.cache import DataStore
    store = DataStore("history")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    store.set(timestamp, rename_history)
    logger.info(f"Rename history saved to DataStore under key: {timestamp}")
