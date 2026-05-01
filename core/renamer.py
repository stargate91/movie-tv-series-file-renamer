from metadata.video_metadata import get_video_metadata
from core.models import Movie, Episode, RenamingTask
import os
import requests
import shutil
import logging

logger = logging.getLogger(__name__)



def format_filename(name, case="none", separator="space"):
    # 1. Clean illegal characters for Windows
    illegal_chars = ['<', '>', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        name = name.replace(char, '')
    
    # Replace colon with space (standard for titles)
    name = name.replace(':', ' ')
    
    # 2. Apply Case
    if case == "lower":
        name = name.lower()
    elif case == "upper":
        name = name.upper()
    elif case == "title":
        name = name.title()

    # 3. Apply Separator
    separator_map = {
        "space": " ",
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }
    sep_char = separator_map.get(separator, " ")

    # Clean up double spaces first
    while "  " in name:
        name = name.replace("  ", " ")
    name = name.strip()

    if sep_char != " ":
        name = name.replace(" ", sep_char)

    return name

def rename_video_files(api_results, live_run, zero_padding, custom_variable,
                      movie_template, episode_template, filename_case, separator,
                      sample_action="rename", sample_suffix="sample", ui=None):
    """
    Renames video files based on enriched Movie/Episode objects.
    Returns a list of RenamingTask objects and a rename history list.
    """
    results = []
    rename_history = []

    total = len(api_results)
    for idx, item in enumerate(api_results, 1):
        if ui:
            ui.update_progress(idx, total, f"Status: Processing {idx}/{total}")
        
        file_path = str(item.file_path)
        file_extension = os.path.splitext(file_path)[1].lower()

        # Tech metadata is already enriched
        tech_meta = item.tech_metadata

        # Prepare template variables
        if isinstance(item, Movie):
            template_vars = item.to_template_dict()
        else:
            # Prepare season/episode strings for TV
            season_str = str(item.season_number)
            episode_str = str(item.episode_number)
            if zero_padding:
                try:
                    season_str = f"{int(item.season_number):02}"
                    episode_str = f"{int(item.episode_number):02}"
                except: pass
            template_vars = item.to_template_dict(season_str, episode_str)

        template_vars["custom_variable"] = custom_variable

        if isinstance(item, Movie):
            new_filename = movie_template.format(**template_vars)
        elif isinstance(item, Episode):
            new_filename = episode_template.format(**template_vars)

        # Safety: If part info exists but was not used in template, append it to avoid collisions
        if item.part and item.part not in new_filename:
            new_filename += f" {item.part}"

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
