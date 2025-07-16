import os
import ffmpeg
from outputs import processing_file_message, getting_resolution_error_message, rename_success_message, dry_rename_success_message
from validators import is_video_file

def get_video_files_from_directory(directory, min_size_bytes):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and is_video_file(file_path, min_size_bytes):
            processing_file_message(file_path)
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_video_files(root_folder, recursive):
    min_size_mb = 500
    min_size_bytes = min_size_mb * 1024 * 1024

    video_files = []

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            video_files.extend(get_video_files_from_directory(root, min_size_bytes))
    else:
        video_files.extend(get_video_files_from_directory(root_folder, min_size_bytes))

    return video_files

def get_resolution_from_file(file_path):
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
        getting_resolution_error_message(file_path, e)
        return "Unknown"

def rename_files(api_results, dry_run, movie_template, episode_template):
    renamed_files = []

    for file_data in api_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']

        resolution = get_resolution_from_file(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_type == "movie":
            movie_details = file_data['movie_details']
            if 'Title' in movie_details:
                movie_title = movie_details['Title']
                movie_year = movie_details['Year']
            elif 'title' in movie_details:
                movie_title = movie_details['title']
                movie_release_date = movie_details['release_date']
                movie_year = release_date.split('-')[0]

                new_filename = movie_template.format(
                    movie_title=movie_title,
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
            
            new_filename = episode_template.format(
                series_title=series_title,
                episode_title=episode_title,
                season=season,
                episode=episode,
                air_date=air_date,
                resolution=resolution
            )

        
        new_filename += file_extension

        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        if not dry_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)
            rename_success_message(file_path, new_filename)
        else:
            dry_rename_success_message(file_path, new_filename)

    return renamed_files
