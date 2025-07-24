def standardize_season_episode_numbers(file_data):
    season = file_data.get('season_file') or file_data.get('season_folder') or 'unknown'
    episode = file_data.get('episode_file') or file_data.get('episode_folder') or 'unknown'

    if season == 'unknown':
        print(f"[WARNING] Missing season number for file data: {file_data}")
    if episode == 'unknown':
        print(f"[WARNING] Missing episode number for file data: {file_data}")

    return season, episode

def standardize_metadata(handled_results):
    if not handled_results:
        print("[INFO] There's nothing to standardize - no movies or episodes had a single match. Others were skipped or cancelled.\nYou can try a different folder or use manual search/selection next time.\nExiting now.")
        return [], []

    standardized_files = []
    unexpected_files = []

    for file_data in handled_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']
        extras = file_data['extras']
        data = file_data['details']

        if file_type == "movie":
            title = data.get('title', 'Unknown Title')
            release_date = data.get('release_date', 'Unknown Release Date')
            if release_date != 'Unknown Release Date':
                year = release_date.split('-')[0]
            else:
                year = 'Unknown Year'

            tmdb_id = data.get('id', 'Unknown ID')
            standardized_files.append({
                'file_path': file_path,
                'file_type': file_type,
                'title': title,
                'release_date': release_date,
                'year': year,
                'tmdb_id': tmdb_id,
                'extras': extras
                })

        if file_type == "episode":
            title = data.get('name', 'Unknown Title')
            first_air_date = data.get('first_air_date', 'Unknown First Air Date')
            if first_air_date != "Unknown First Air Date":
                first_air_year = first_air_date.split('-')[0]
            else:
                first_air_year = 'Unknown First Air Year'
            tmdb_id = data.get('id', 'Unknown ID')
            season_number, episode_number = standardize_season_episode_numbers(file_data)

            if 'unknown' in [season_number, episode_number]:
                print(f"[WARNING] Unexpected files for {file_data['file_path']}.")
                unexpected_files.append(file_data)

            standardized_files.append({
                'file_path': file_path,
                'file_type': file_type,
                'series_title': title,
                'season_number': season_number,
                'episode_number': episode_number,
                'first_air_date': first_air_date,
                'first_air_year': first_air_year,
                'tmdb_id': tmdb_id,
                'extras': extras
                })

    return standardized_files, unexpected_files
