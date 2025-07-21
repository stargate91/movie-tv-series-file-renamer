from datetime import datetime

def normalize_movies(movies, source=None):

    if not movies:
        print(f"\n[INFO] There are no movies to normalize in this pack: {source}.\n")
        return []
    
    normalized_movies = []

    for file_data in movies:
        movie_details = file_data['details']

        if movie_details.get('results'):
            movie_details = movie_details['results'][0]

        if 'release_date' in movie_details:
            movie_details.update({'year': movie_details['release_date'].split('-')[0]})

        if 'Title' in movie_details:
            movie_details['title'] = movie_details.pop('Title')

        if 'Released' in movie_details:
            movie_details['release_date'] = movie_details.pop('Released')
            movie_details['release_date'] = datetime.strptime(movie_details['release_date'], "%d %b %Y").strftime("%Y-%m-%d")

        if 'Year' in movie_details:
            movie_details['year'] = movie_details.pop('Year')

        normalized_movies.append({
            'file_path': file_data['file_path'],
            'file_type': file_data['file_type'],
            'extras': file_data['extras'],
            'movie_details': movie_details
            })

    return normalized_movies

def normalize_season_episode_numbers(file_data):
    season = file_data.get('season_file') or file_data.get('season_folder') or 'unknown'
    episode = file_data.get('episode_file') or file_data.get('episode_folder') or 'unknown'

    if season == 'unknown':
        print(f"[WARNING] Missing season number for file data: {file_data}")
    if episode == 'unknown':
        print(f"[WARNING] Missing episode number for file data: {file_data}")

    return season, episode

def normalize_episodes(episodes, api_client, source=None):

    if not episodes:
        print(f"\n[INFO] There are no episodes to normalize in this pack: {source}.\n")
        return [], []

    normalized_episodes = []
    unexpected_files = []

    for file_data in episodes:

        details = file_data.get("details", {})

        if "results" in details:
            if details["results"]:
                series_details = details["results"][0]
            else:
                print(f"[ERROR] Empty results in details for: {file_data['file_path']}")
                unexpected_files.append(file_data)
                continue
        else:
            series_details = details

        series_id = series_details['id']
        series_details.update({'first_air_year': series_details['first_air_date'].split('-')[0]})

        if 'name' in series_details:
            series_details['title'] = series_details.pop('name')

        season, episode = normalize_season_episode_numbers(file_data)

        series_data = api_client.get_from_tmdb_tv_detail(series_id)
        if series_data.get('status') == "Ended":
            last_air_date = series_data.get('last_air_date')
            if last_air_date:
                series_details.update({
                    'status': series_data.get('status', 'unknown'),
                    'last_air_date': last_air_date,
                    'last_air_year': last_air_date.split('-')[0]
                })
            else:
                series_details.update({
                    'status': series_data.get('status', 'unknown'),
                    'last_air_date': 'unknown',
                    'last_air_year': 'unknown'
                })
        else:
            series_details.update({
                'status': series_data.get('status', 'unknown'),
                'last_air_date': 'unknown',
                'last_air_year': 'unknown'                
            })

        if 'unknown' in [season, episode]:
            print(f"[WARNING] Unexpected files for {file_data['file_path']}. Manual renaming needed.")
            unexpected_files.append(file_data)
        else:
            normalized_episodes.append({
                'file_path': file_data['file_path'],
                'file_type': file_data['file_type'],
                'extras': file_data['extras'],
                'season': season,
                'episode': episode,
                'series_details': series_details
            })

    return normalized_episodes, unexpected_files
