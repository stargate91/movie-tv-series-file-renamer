from outputs import proc_file_msg, res_error_msg, rename_success_msg, dry_rename_msg
from validators import is_vid_file
from datetime import datetime
import ffmpeg
import os

def get_vid_files(directory, min_size_bytes, root_folder):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and is_vid_file(file_path, min_size_bytes):
            proc_file_msg(file_path, root_folder)
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_vid_files_all(root_folder, recursive):
    min_size_mb = 500
    min_size_bytes = min_size_mb * 1024 * 1024

    video_files = []

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            video_files.extend(get_vid_files(root, min_size_bytes, root_folder))
    else:
        video_files.extend(get_vid_files(root_folder, min_size_bytes, root_folder))

    return video_files

def get_res(file_path):
    try:
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='stream=width,height')
        width = probe['streams'][0]['width']
        height = probe['streams'][0]['height']
        
        if width >= 1920:
            return '1080p'
        elif width >= 1280:
            return '720p'
        else:
            return '480p'
    except ffmpeg._run.Error as e:
        res_error_msg(file_path, e)
        return "unknown"

def rename_vid_files(api_results, live_run, zero_padding, movie_template, episode_template):
    renamed_files = []

    for file_data in api_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']

        resolution = get_res(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_type == "movie":
            movie_details = file_data['movie_details']
            if 'Title' in movie_details:
                movie_title = movie_details['Title']
                movie_year = movie_details['Year']
                released = movie_details['Released']
                movie_release_date = datetime.strptime(released, "%d %b %Y").strftime("%Y-%m-%d")
            elif 'title' in movie_details:
                movie_title = movie_details['title']
                movie_release_date = movie_details['release_date']
                movie_year = movie_release_date.split('-')[0]

            new_filename = movie_template.format(
                movie_title=movie_title,
                movie_release_date=movie_release_date,
                movie_year=movie_year,
                resolution=resolution
                )
        elif file_type == "episode":
            series_details = file_data['series_details']
            episode_details = file_data['episode_details']
            episode_title = episode_details['name']
            season = episode_details['season_number']
            episode = episode_details['episode_number']
            air_date = episode_details['air_date']
            series_title = series_details['name']
            first_air_date = series_details['first_air_date']
            
            if "zero_padding":
                season_str = f"{season:02}"
                episode_str = f"{episode:02}"
            else:
                season_str = str(season)
                episode_str = str(episode)

            new_filename = episode_template.format(
                series_title=series_title,
                episode_title=episode_title,
                season=season_str,
                episode=episode_str,
                air_date=air_date,
                resolution=resolution
            )
        
        new_filename += file_extension

        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        if live_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)
            rename_success_msg(file_path, new_filename)
        else:
            dry_rename_msg(file_path, new_filename)

    return renamed_files
