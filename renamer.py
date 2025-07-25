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
    rename_history = []

    for file_data in api_results:
        file_path = file_data['file_path']
        file_type = file_data['file_type']
        genres = file_data.get('genres')
        imdb_rating = file_data.get('imdb_rating')
        rotten_rating = file_data.get('rotten_rating')
        metacritic_rating = file_data.get('metacritic_rating')

        extras = file_data['extras']
        release_group = extras.get('release_group', 'Unknown Release Group')
        source = extras.get('source', 'Unknown Source')
        other = extras.get('other', 'Unknown')
        edition = extras.get('edition', 'Unknown Edition')
        streaming_service = extras.get('streaming_service', 'Unknown Streaming Service')

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
            movie_title = file_data.get('title')
            movie_release_date = file_data.get('release_date')
            movie_year = file_data.get('year')

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
                custom_variable=custom_variable,
                genres=genres,
                imdb_rating=imdb_rating,
                rotten_rating=rotten_rating,
                metacritic_rating=metacritic_rating
            )

        elif file_type == "episode":
            series_title = file_data.get('series_title')
            last_air_date = file_data.get('last_air_date')
            last_air_year = file_data.get('last_air_year')
            episode_title = file_data.get('episode_title')
            season_number = file_data.get('season_number')
            episode_number = file_data.get('episode_number')
            first_air_date = file_data.get('first_air_date')
            first_air_year = file_data.get('first_air_year')
            last_air_date = file_data.get('last_air_date')
            last_air_year = file_data.get('last_air_year')
            air_date = file_data.get('air_date')
            air_year = file_data.get('air_year')
            status = file_data.get('status')

            if zero_padding:
                season_str = f"{season_number:02}"
                episode_str = f"{episode_number:02}"
            else:
                season_str = str(season_number)
                episode_str = str(episode_number)

            new_filename = episode_template.format(
                series_title=series_title,
                first_air_date=first_air_date,
                first_air_year=first_air_year,
                last_air_date=last_air_date,
                last_air_year=last_air_year,
                status=status,
                episode_title=episode_title,
                season_number=season_str,
                episode_number=episode_str,
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
                custom_variable=custom_variable,
                genres=genres,
                imdb_rating=imdb_rating,
                rotten_rating=rotten_rating,
                metacritic_rating=metacritic_rating
            )

        name_without_ext = format_filename(new_filename, filename_case, separator)
        new_filename = name_without_ext + file_extension

        file_path = str(file_path)
        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        if live_run:
            os.rename(file_path, new_file_path)
            renamed_files.append(new_file_path)
            rename_history.append((file_path, new_file_path))
            rename_success_message(file_path, new_filename)
        else:
            dry_rename_message(file_path, new_filename)

    return renamed_files, rename_history
