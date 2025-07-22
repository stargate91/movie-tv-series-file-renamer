import os

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
    "done":            ("🎉 ", "")
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
        'omdb': api_client.get_from_omdb,
        'tmdb': api_client.get_from_tmdb_movie,
        'tmdb_tv': api_client.get_from_tmdb_tv
    }.get(source)

def has_results(result, source):
    if source == 'omdb':
        return result.get("Response") == "True"
    if source in {'tmdb', 'tmdb_tv'}:
        return result.get("total_results", 0) > 0
    return False

def extract_results(result, source):
    if source == 'omdb':
        return [result]
    if source in {'tmdb', 'tmdb_tv'}:
        return result.get('results', [])
    return []

def search_api(api_client, source, title, year):
    api_func = get_api_func(api_client, source)
    result = api_func(title, year)
    results = extract_results(result, source) if result else []
    return result, results
