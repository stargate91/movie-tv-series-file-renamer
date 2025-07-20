from meta_from_files import ( 
    get_res,
    get_codec,
    get_video_bitrate,
    get_framerate, 
    get_audio_codec,
    get_audio_channels,
    get_first_audio_language_code,
    get_audio_channel_description
)
from outputs import proc_file_msg, rename_success_msg, dry_rename_msg
import os
import pycountry
import ffmpeg

def is_vid_file(file_path, min_size_bytes):
    file_extension = os.path.splitext(file_path)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']

    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False

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

def get_video_metadata(file_path):
    metadata = {}
    metadata['resolution'] = get_res(file_path)
    metadata['video_codec'] = get_codec(file_path)
    metadata['video_bitrate'] = get_video_bitrate(file_path)
    metadata['framerate'] = get_framerate(file_path)
    metadata['audio_codec'] = get_audio_codec(file_path)
    metadata['audio_channels'] = get_audio_channels(file_path)
    metadata['first_audio_channel_language'] = get_first_audio_language_code(file_path)
    metadata['audio_channels_description'] = get_audio_channel_description(file_path)
    return metadata


def rename_vid_files(api_results, live_run, zero_padding, movie_template, episode_template):
    renamed_files = []

    for file_data in api_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']

        resolution = get_res(file_path)
        video_codec = get_codec(file_path)
        video_bitrate = get_video_bitrate(file_path)
        framerate = get_framerate(file_path)
        audio_codec = get_audio_codec(file_path)
        audio_channels = get_audio_channels(file_path)
        first_audio_channel_language = get_first_audio_language_code(file_path)
        audio_channels_description = get_audio_channel_description(file_path)

        file_extension = os.path.splitext(file_path)[1].lower()

        if file_type == "movie":
            movie_details = file_data['movie_details']
            movie_title = movie_details['title']
            movie_year = movie_details['year']
            movie_release_date = movie_details['release_date']

            new_filename = movie_template.format(
                movie_title=movie_title,
                movie_release_date=movie_release_date,
                movie_year=movie_year,
                resolution=resolution,
                video_codec=video_codec,
                video_bitrate=video_bitrate,
                framerate=framerate,
                audio_codec=audio_codec,
                audio_channels=audio_channels,
                first_audio_channel_language=first_audio_channel_language,
                audio_channels_description=audio_channels_description
                )
        elif file_type == "episode":
            series_details = file_data['series_details']
            series_title = series_details['title']
            first_air_date = series_details['first_air_date']
            first_air_year = series_details['first_air_year']
            last_air_date = series_details['last_air_date']
            last_air_year = series_details['last_air_year']
            status = series_details['status']

            episode_details = file_data['episode_details']
            episode_title = episode_details['name']
            season = episode_details['season_number']
            episode = episode_details['episode_number']
            air_date = episode_details['air_date']
            air_year = air_date.split('-')[0]

            
            if "zero_padding":
                season_str = f"{season:02}"
                episode_str = f"{episode:02}"
            else:
                season_str = str(season)
                episode_str = str(episode)

            new_filename = episode_template.format(
                series_title=series_title,
                first_air_date=first_air_date,
                first_air_year=first_air_year,
                last_air_date=last_air_date,
                last_air_year=last_air_year,
                status=status,
                episode_title=episode_title,
                season=season_str,
                episode=episode_str,
                air_date=air_date,
                air_year=air_year,
                resolution=resolution,
                video_codec=video_codec,
                video_bitrate=video_bitrate,
                framerate=framerate,
                audio_codec=audio_codec,
                audio_channels=audio_channels,
                first_audio_channel_language=first_audio_channel_language,
                audio_channels_description=audio_channels_description
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
