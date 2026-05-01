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

    # Safety for CD parts: prevent 'Cd1' if using Title Case
    if case != "lower":
        import re
        # Find Cd followed by numbers and make it CD
        name = re.sub(r'\bCd(\d+)\b', r'CD\1', name)

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

    # --- PASS 1: Calculate names and detect collisions ---
    for item in api_results:
        file_path = str(item.file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Prepare template variables
        if isinstance(item, Movie):
            template_vars = item.to_template_dict()
        else:
            season_str = str(item.season_number)
            episode_str = str(item.episode_number)
            if zero_padding:
                try:
                    season_str = f"{int(item.season_number):02}"
                    episode_str = f"{int(item.episode_number):02}"
                except: pass
            template_vars = item.to_template_dict(season_str, episode_str)

        template_vars["custom_variable"] = custom_variable
        
        try:
            if isinstance(item, Movie):
                new_filename = movie_template.format(**template_vars)
            elif isinstance(item, Episode):
                new_filename = episode_template.format(**template_vars)
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            new_filename = os.path.basename(file_path).replace(file_extension, "")

        # Safety: If part info exists but was not used in template, append it to avoid collisions
        if item.part and item.part not in new_filename:
            new_filename += f" {item.part}"

        name_without_ext = format_filename(new_filename, filename_case, separator)
        new_filename = name_without_ext + file_extension

        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        main_task = RenamingTask(
            old_path=file_path,
            new_filename=new_filename,
            new_path=new_file_path,
        )
        results.append(main_task)

        # Handle associated samples
        if hasattr(item, 'associated_samples') and item.associated_samples:
            for sample_path in item.associated_samples:
                if sample_action == "ignore": continue
                
                if sample_action == "delete":
                    results.append(RenamingTask(old_path=sample_path, new_filename="DELETED", new_path="", status="pending"))
                elif sample_action == "rename":
                    sample_ext = os.path.splitext(sample_path)[1].lower()
                    raw_sample_name = f"{name_without_ext} {sample_suffix}"
                    formatted_sample_name = format_filename(raw_sample_name, filename_case, separator) + sample_ext
                    sample_new_path = os.path.join(directory, formatted_sample_name)
                    results.append(RenamingTask(old_path=sample_path, new_filename=formatted_sample_name, new_path=sample_new_path, status="pending"))

    # Collision Detection logic
    path_counts = {}
    for task in results:
        if not task.new_path: continue
        p = os.path.abspath(task.new_path)
        path_counts[p] = path_counts.get(p, 0) + 1
    
    for task in results:
        if not task.new_path: continue
        p = os.path.abspath(task.new_path)
        if path_counts[p] > 1:
            task.has_collision = True
        if os.path.exists(task.new_path) and os.path.abspath(task.new_path) != os.path.abspath(task.old_path):
            task.has_collision = True

    # --- PASS 2: Execute (if live_run and NO collisions in entire batch) ---
    if live_run:
        # Safety check: If there's even one collision, abort the whole batch for safety
        has_any_collision = any(task.has_collision for task in results)
        
        if has_any_collision:
            logger.error("Batch rename aborted: Collisions detected.")
            for task in results:
                if task.has_collision:
                    task.status = "error"
                    task.error_message = "CRITICAL: Collision detected. Batch aborted for safety."
                else:
                    task.status = "dry_run" # Revert to dry run status for UI
            return results, rename_history

        total_ops = len(results)
        for idx, task in enumerate(results):
            try:
                if task.new_filename == "DELETED":
                    os.remove(task.old_path)
                else:
                    if os.path.abspath(task.old_path) != os.path.abspath(task.new_path):
                        os.rename(task.old_path, task.new_path)
                        rename_history.append((task.old_path, task.new_path))
                task.status = "success"
            except Exception as e:
                task.status = "error"
                task.error_message = str(e)
            
            if ui:
                ui.update_progress(idx + 1, total_ops, f"Processing: {idx + 1}/{total_ops}")
    else:
        for task in results:
            if task.status == "pending":
                task.status = "dry_run"

    return results, rename_history
