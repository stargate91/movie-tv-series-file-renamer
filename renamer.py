from video_metadata import get_video_metadata
from ui_ux import rename_starts_message, rename_success_message, dry_rename_message
import os

def format_filename(name, case="none", separator="space"):
    if case == "lower":
        name = name.lower()
    elif case == "upper":
        name = name.upper()
    elif case == "title":
        name = name.title()

    separator_map = {
        "space": " ",
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    sep_char = separator_map.get(separator, " ")

    if sep_char != " ":
        name = name.replace(" ", sep_char)

    return name

def rename_video_files(api_results, live_run, zero_padding, custom_variable,
                     movie_template, episode_template, use_emojis,
                     filename_case, separator):
    rename_starts_message(live_run, use_emojis)
    renamed_files = []

    for file_data in api_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']
        extras = file_data.get('extras', {})
        release_group = extras.get('release_group', 'unknown')
        source = extras.get('source', 'unknown')
        other = extras.get('other', 'unknown')
        edition = extras.get('edition', 'unknown')
        streaming_service = extras.get('streaming_service', 'unknown')

        metadata = get_video_metadata(file_path)
        resolution = metadata['resolution']
        video_codec = metadata['video_codec']
        video_bitrate = metadata['video_bitrate']
        framerate = metadata['framerate']
        audio_codec = metadata['audio_codec']
        audio_channels = metadata['audio_channels']
        first_audio_channel_language = metadata['first_audio_channel_language']
        audio_channels_description = metadata['audio_channels_description']

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
                audio_channels_description=audio_channels_description,
                release_group=release_group,
                source=source,
                other=other,
                edition=edition,
                streaming_service=streaming_service,
                custom_variable=custom_variable
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

            if zero_padding:
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
                audio_channels_description=audio_channels_description,
                release_group=release_group,
                source=source,
                other=other,
                edition=edition,
                streaming_service=streaming_service,
                custom_variable=custom_variable
            )

        name_without_ext = format_filename(new_filename, filename_case, separator)
        new_filename = name_without_ext + file_extension

        file_path = str(file_path)
        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        if live_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)
            rename_success_message(file_path, new_filename)
        else:
            dry_rename_message(file_path, new_filename)

    return renamed_files
