import os
import traceback

def normalize_season_episode(file_data):
    season = file_data.get('season_file') or file_data.get('season_folder') or 'unknown'
    episode = file_data.get('episode_file') or file_data.get('episode_folder') or 'unknown'

    if season == 'unknown':
        print(f"[WARNING] Missing season number for file data: {file_data}")
    if episode == 'unknown':
        print(f"[WARNING] Missing episode number for file data: {file_data}")

    return season, episode

def normalize_episodes(episodes, api_client):
    handled_files = []
    unexpected_files = []

    for file_data in episodes:
        data = file_data['details']
        season_details = data['results'][0]
        series_id = season_details['id']
        season_details.update({'first_air_year': season_details['first_air_date'].split('-')[0]})
        season_details['title'] = season_details.pop('name')

        season, episode = normalize_season_episode(file_data)

        try:
            season_data = api_client.get_from_tmdb_tv_detail(series_id)
            if season_data.get('status') == "Ended":
                last_air_date = season_data.get('last_air_date')
                if last_air_date:
                    season_details.update({
                        'last_air_date': last_air_date,
                        'last_air_year': last_air_date.split('-')[0]
                    })
                else:
                    season_details.update({
                        'last_air_date': 'unknown',
                        'last_air_year': 'unknown'
                    })
            else:
                season_details.update({
                    'status': season_data.get('status', 'unknown')
                })
        except Exception as e:
            print(f"[ERROR] API error for {file_data['file_path']}: {e}")

        if 'unknown' in [season, episode]:
            print(f"[WARNING] Unexpected files for {file_data['file_path']}. Manual renaming needed.")
            unexpected_files.append(file_data)
        else:
            handled_files.append({
                'file_path': file_data['file_path'],
                'file_type': file_data['file_type'],
                'extras': file_data['extras'],
                'season': season,
                'episode': episode,
                'season_details': season_details
            })

    return handled_files, unexpected_files

