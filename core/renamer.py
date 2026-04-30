from metadata.video_metadata import get_video_metadata
from core.models import Movie, Episode, RenamingTask
import os
import requests
import shutil
import logging

logger = logging.getLogger(__name__)

def download_poster(url, target_path):
    try:
        if not url: return False
        # Use large image for saved poster
        large_url = url.replace("/w200/", "/original/").replace("/w500/", "/original/")
        response = requests.get(large_url, stream=True, timeout=15)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            return True
    except Exception as e:
        logger.error(f"Failed to download poster: {e}")
    return False

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
                      movie_template, episode_template, filename_case, separator,
                      sample_action="rename", sample_suffix="sample",
                      download_posters=False):
    """
    Renames video files based on enriched Movie/Episode objects.
    Returns a list of RenamingTask objects and a rename history list.
    """
    results = []
    rename_history = []

    for item in api_results:
        file_path = str(item.file_path)
        file_extension = os.path.splitext(file_path)[1].lower()

        # Get technical metadata from the actual video file
        tech_meta = get_video_metadata(file_path)

        # Common template variables (tech + custom)
        common_vars = {
            "resolution": tech_meta['resolution'],
            "video_codec": tech_meta['video_codec'],
            "video_bitrate": tech_meta['video_bitrate'],
            "framerate": tech_meta['framerate'],
            "audio_codec": tech_meta['audio_codec'],
            "audio_channels": tech_meta['audio_channels'],
            "first_audio_channel_language": tech_meta['first_audio_channel_language'],
            "audio_channels_description": tech_meta['audio_channels_description'],
            "hdr_type": tech_meta['hdr_type'],
            "bit_depth": tech_meta['bit_depth'],
            "subtitle_languages": tech_meta['subtitle_languages'],
            "audio_streams_count": tech_meta['audio_streams_count'],
            "custom_variable": custom_variable,
        }

        if isinstance(item, Movie):
            template_vars = {**item.to_template_dict(), **common_vars}
            new_filename = movie_template.format(**template_vars)

        elif isinstance(item, Episode):
            if zero_padding:
                season_str = f"{item.season_number:02}"
                episode_str = f"{item.episode_number:02}"
            else:
                season_str = str(item.season_number)
                episode_str = str(item.episode_number)

            template_vars = {**item.to_template_dict(season_str, episode_str), **common_vars}
            new_filename = episode_template.format(**template_vars)

        name_without_ext = format_filename(new_filename, filename_case, separator)
        new_filename = name_without_ext + file_extension

        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        task = RenamingTask(
            old_path=file_path,
            new_filename=new_filename,
            new_path=new_file_path,
        )

        if live_run:
            try:
                os.rename(file_path, new_file_path)
                task.status = "success"
                rename_history.append((file_path, new_file_path))

                # Download poster if enabled
                if download_posters and item.poster_path:
                    poster_url = f"https://image.tmdb.org/t/p/w500{item.poster_path}"
                    poster_target = os.path.join(directory, "poster.jpg")
                    # Only download if it doesn't exist yet
                    if not os.path.exists(poster_target):
                        download_poster(poster_url, poster_target)

            except Exception as e:
                task.status = "error"
                task.error_message = str(e)
        else:
            task.status = "dry_run"

        results.append(task)

        # Handle associated samples
        if hasattr(item, 'associated_samples') and item.associated_samples:
            for sample_path in item.associated_samples:
                if sample_action == "ignore":
                    continue

                if sample_action == "delete":
                    sample_task = RenamingTask(
                        old_path=sample_path,
                        new_filename="DELETED",
                        new_path="",
                    )
                    if live_run:
                        try:
                            os.remove(sample_path)
                            sample_task.status = "success"
                        except Exception as e:
                            sample_task.status = "error"
                            sample_task.error_message = str(e)
                    else:
                        sample_task.status = "dry_run"
                    results.append(sample_task)

                elif sample_action == "rename":
                    sample_ext = os.path.splitext(sample_path)[1].lower()
                    raw_sample_name = f"{new_filename.replace(file_extension, '')} {sample_suffix}"
                    formatted_sample_name = format_filename(raw_sample_name, filename_case, separator) + sample_ext
                    sample_new_path = os.path.join(directory, formatted_sample_name)

                    sample_task = RenamingTask(
                        old_path=sample_path,
                        new_filename=formatted_sample_name,
                        new_path=sample_new_path,
                    )
                    if live_run:
                        try:
                            os.rename(sample_path, sample_new_path)
                            sample_task.status = "success"
                            rename_history.append((sample_path, sample_new_path))
                        except Exception as e:
                            sample_task.status = "error"
                            sample_task.error_message = str(e)
                    else:
                        sample_task.status = "dry_run"
                    results.append(sample_task)

    return results, rename_history
