import os
import ffmpeg

def is_video_file(file_path, min_size_bytes):
    file_extension = os.path.splitext(file_path)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']

    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False

def get_video_files_from_directory(directory, min_size_bytes):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and is_video_file(file_path, min_size_bytes):
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
            return 1080
        elif width >= 1280:
            return 720
        else:
            return 480
    except ffmpeg._run.Error as e:
        print(f"Error getting resolution for {file_path}: {e}")
        return "Unknown"


def rename_movie_files(api_results, dry_run):
    renamed_files = []

    for file_data in api_results: 
        file_path = file_data['file_path']
        metadata = file_data['data']

        if 'Title' in metadata:
            title = metadata['Title']
            year = metadata['Year']
        elif 'title'in metadata:
            title = metadata['title']
            release_date = metadata['release_date']
            year = release_date.split('-')[0]
        elif 'results' in metadata:
            title = metadata['results'][0]['title']
            release_date = metadata['results'][0]['release_date']
            year = release_date.split('-')[0]
        else:
            print("[ERROR] Missing title or year from API response.")
            continue


        resolution = get_resolution_from_file(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        new_filename = f"{title} - {year}_{resolution}p{file_extension}"
        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        print(f"Old name: {file_path} -> New name: {new_filename}")

        if not dry_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)

    return renamed_files

def rename_series_files(api_results, dry_run):
    renamed_files = []

    for file_data in api_results: 
        file_path = file_data['file_path']

        series_details = file_data['series_details']
        episode_details = file_data['episode_details']

        episode_title = episode_details['name']
        season = episode_details['season_number']
        episode = episode_details['episode_number']
        air_date = episode_details['air_date']

        series_title = series_details['name']
        first_air_date = series_details['first_air_date']


        resolution = get_resolution_from_file(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        new_filename = f"{series_title} - S{season}E{episode} - {episode_title} - {air_date}_{resolution}p{file_extension}"
        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        print(f"Old name: {file_path} -> New name: {new_filename}")

        if not dry_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)

    return renamed_files