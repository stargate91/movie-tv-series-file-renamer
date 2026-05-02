from metadata.video_metadata import get_video_metadata
from core.models import Movie, Episode, RenamingTask
import os
import requests
import shutil
import logging

logger = logging.getLogger(__name__)

def get_preview_name(path, meta, settings, metadata_map=None):
    """Generates a raw (unformatted) preview name based on metadata and settings."""
    if not meta or meta.get('status') not in ['one_match', 'multi_match']:
        return os.path.splitext(os.path.basename(path))[0]
    
    details = meta.get('details', {})
    if not details:
        return os.path.splitext(os.path.basename(path))[0]

    try:
        class SafeDict(dict):
            def __missing__(self, key):
                return f"{{{key}}}"

        if meta.get('file_type') == 'movie':
            from core.models import Movie
            model = Movie.from_dict(details)
            if not model: return os.path.splitext(os.path.basename(path))[0]
            
            # Determine is_multi for preview (rough guess)
            is_multi = False
            if metadata_map and model.part:
                is_multi = any(m.get('tmdb_id') == model.tmdb_id and m.get('file_path') != path for m in metadata_map.values())
            
            vars = SafeDict(model.to_template_dict(is_multi=is_multi))
            # Provide alias 'title' for convenience
            vars['title'] = model.title
            return settings.movie_template.format_map(vars)
        elif meta.get('file_type') == 'episode':
            from core.models import Episode
            model = Episode.from_dict(details)
            if not model: return os.path.splitext(os.path.basename(path))[0]
            
            # Handle multi-episode lists
            s_val = model.season_number[0] if isinstance(model.season_number, list) else model.season_number
            e_vals = model.episode_number if isinstance(model.episode_number, list) else [model.episode_number]
            
            if settings.zero_padding:
                try:
                    sn = f"{int(s_val):02}"
                    en = "-".join([f"{int(e):02}" for e in e_vals])
                except: 
                    sn = str(s_val)
                    en = "-".join([str(e) for e in e_vals])
            else:
                sn = str(s_val)
                en = "-".join([str(e) for e in e_vals])
            
            # Determine is_multi for preview (rough guess)
            is_multi = False
            if metadata_map and model.part:
                is_multi = any(m.get('tmdb_id') == model.tmdb_id and m.get('file_path') != path for m in metadata_map.values())
            
            vars = SafeDict(model.to_template_dict(sn, en, is_multi=is_multi))
            # Provide aliases for convenience
            vars['title'] = model.episode_title
            vars['series'] = model.series_title
            return settings.episode_template.format_map(vars)
    except Exception as e:
        logger.error(f"Preview formatting error: {e}")

    if meta.get('file_type') == 'extra':
        from core.renamer import format_filename
        from core.models import Movie, Episode
        tmpl = settings.extra_template
        e_type = meta.get('extra_type', 'Sample')
        orig_base = os.path.splitext(os.path.basename(path))[0]
        
        # Start with own variables
        vars = SafeDict({
            "extra_type": e_type,
            "original": orig_base,
            "parent": "Parent"
        })

        parent_path = meta.get('extra_parent')
        if parent_path and metadata_map:
            # Resolve parent path
            parent_abs = os.path.abspath(parent_path) if os.path.isabs(parent_path) else os.path.abspath(os.path.join(os.path.dirname(path), parent_path))
            
            # Try absolute match, then try basename match as fallback
            p_meta = metadata_map.get(parent_abs) or metadata_map.get(parent_path)
            if not p_meta:
                # Last ditch effort: find by filename
                p_base = os.path.basename(parent_path)
                for m_path, m_val in metadata_map.items():
                    if os.path.basename(m_path) == p_base:
                        p_meta = m_val
                        break
            
            # Use parent's basename as the default 'parent' variable
            vars['parent'] = os.path.splitext(os.path.basename(parent_path))[0]
            
            # LAST DITCH FALLBACK: If parent name is too technical or generic, try to parse it
            if vars['parent'].lower() in ['sample', 'trailer', 'extra', 'parent']:
                try:
                    from metadata.video_metadata import get_video_metadata
                    # We don't have full metadata, but we can try to guess title from path
                    guessed = get_video_metadata(path)
                    if guessed and guessed.get('details'):
                        vars['parent'] = guessed['details'].get('title') or vars['parent']
                except: pass

            if p_meta and p_meta.get('details'):
                p_details = p_meta['details']
                # Pick the correct template based on parent type
                if p_meta.get('file_type') == 'movie':
                    tmpl = settings.movie_extra_template
                    from core.models import Movie
                    p_model = Movie.from_dict(p_details)
                    if p_model:
                        vars.update(p_model.to_template_dict())
                        vars['parent'] = p_model.title
                        # Also add generic variables just in case
                        vars['title'] = p_model.title
                        vars['year'] = p_model.year
                elif p_meta.get('file_type') == 'episode':
                    tmpl = settings.episode_extra_template
                    from core.models import Episode
                    p_model = Episode.from_dict(p_details)
                    if p_model:
                        vars.update(p_model.to_template_dict("01", "01"))
                        vars['parent'] = p_model.episode_title
                        vars['title'] = p_model.episode_title
                        vars['series'] = p_model.series_title

        return format_filename(tmpl.format_map(vars), settings.filename_case, settings.separator)

    return os.path.splitext(os.path.basename(path))[0]

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
                      extra_action="rename", extra_template="{parent} - {extra_type}", 
                      movie_extra_template=None, episode_extra_template=None,
                      settings=None, metadata_map=None, ui=None):
    """
    Renames video files based on enriched Movie/Episode objects.
    Also handles Extras based on the provided metadata_map and settings.
    """
    results = []
    rename_history = []
    
    # 1. Map to find final names of main features (needed for {parent} template in extras)
    main_feature_names = {} # old_path -> new_name_without_ext

    # --- PASS 0: Build a complete Map of ALL potential Parents ---
    # This ensures Extras can find their parents even if the parent is not in the current rename batch
    parent_models = {} # abs_path -> (model, season_str, episode_str)
    if metadata_map:
        for p, meta in metadata_map.items():
            if meta.get('file_type') == 'extra': continue
            
            abs_p = os.path.abspath(p)
            details = meta.get('details')
            if details:
                if meta.get('file_type') == 'movie':
                    parent_models[abs_p] = (Movie.from_dict(details), "", "")
                elif meta.get('file_type') == 'episode':
                    # Extract season/ep from details if available
                    model = Episode.from_dict(details)
                    s = str(details.get('season_number', '01'))
                    e = str(details.get('episode_number', '01'))
                    parent_models[abs_p] = (model, s, e)
            
            name = os.path.splitext(os.path.basename(p))[0]
            main_feature_names[abs_p] = name
            main_feature_names[os.path.basename(p)] = name

    # --- PASS 1: Calculate names for Main Features (Movies/Episodes) ---
    for item in api_results:
        file_path = str(item.file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Calculate is_multi for this item
        is_multi = item.part and any(x for x in api_results if x != item and x.tmdb_id == item.tmdb_id and x.file_type == item.file_type)

        # Prepare template variables
        if isinstance(item, Movie):
            template_vars = item.to_template_dict(is_multi=is_multi)
        else:
            # Handle multi-episode lists
            s_val = item.season_number[0] if isinstance(item.season_number, list) else item.season_number
            e_vals = item.episode_number if isinstance(item.episode_number, list) else [item.episode_number]
            
            if zero_padding:
                try:
                    season_str = f"{int(s_val):02}"
                    episode_str = "-".join([f"{int(e):02}" for e in e_vals])
                except:
                    season_str = str(s_val)
                    episode_str = "-".join([str(e) for e in e_vals])
            else:
                season_str = str(s_val)
                episode_str = "-".join([str(e) for e in e_vals])
            
            template_vars = item.to_template_dict(season_str, episode_str, is_multi=is_multi)

        template_vars["custom_variable"] = custom_variable
        
        try:
            if isinstance(item, Movie):
                new_filename = movie_template.format(**template_vars)
            elif isinstance(item, Episode):
                new_filename = episode_template.format(**template_vars)
        except Exception as e:
            logger.error(f"Template formatting error: {e}")
            new_filename = os.path.basename(file_path).replace(file_extension, "")

        # Use CollisionManager for final naming
        from core.collision_manager import CollisionManager
        collision_mgr = CollisionManager(settings)

        # Get part from metadata_map if available (set by UI)
        abs_p = os.path.abspath(file_path)
        part_num = None
        if metadata_map and abs_p in metadata_map:
            part_num = metadata_map[abs_p].get('part')
        
        # If no manual part, but it's a multi-part file, try to guess order
        if not part_num and item.part and is_multi:
            try:
                # Extract number from "Part 1" or similar
                import re
                nums = re.findall(r'\d+', str(item.part))
                if nums:
                    part_num = int(nums[0])
            except: pass

        name_without_ext = format_filename(new_filename, filename_case, separator)
        
        # Apply collision resolution if we have a part number
        if part_num:
            name_without_ext = collision_mgr.resolve_collision(name_without_ext, part_num)
        
        # Update map with the FUTURE name (overwrites Pass 0 fallback)
        abs_p = os.path.abspath(file_path)
        main_feature_names[abs_p] = name_without_ext
        main_feature_names[os.path.basename(file_path)] = name_without_ext
        
        new_filename = name_without_ext + file_extension
        directory = os.path.dirname(file_path)
        new_file_path = os.path.join(directory, new_filename)

        results.append(RenamingTask(
            old_path=file_path,
            new_filename=new_filename,
            new_path=new_file_path,
        ))

    # Track which main features are being renamed in this batch
    processed_main_paths = {os.path.abspath(str(item.file_path)) for item in api_results}

    # --- PASS 2: Calculate names for Extras ---
    if metadata_map:
        for path, meta in metadata_map.items():
            if meta.get('file_type') != 'extra': continue
            if extra_action == "skip": continue
            
            file_path = os.path.abspath(path)
            
            # Check if parent is being processed in this batch
            parent_path = meta.get('extra_parent')
            if parent_path:
                parent_abs = os.path.abspath(os.path.join(os.path.dirname(file_path), parent_path))
                if parent_abs not in processed_main_paths:
                    logger.info(f"Skipping extra '{os.path.basename(file_path)}' because parent is not being renamed.")
                    continue
            
            file_extension = os.path.splitext(file_path)[1].lower()
            directory = os.path.dirname(file_path)
            
            if extra_action == "delete":
                results.append(RenamingTask(old_path=file_path, new_filename="DELETED", new_path="", status="pending"))
                continue
                
            # Get parent info
            parent_path = meta.get('extra_parent')
            extra_vars = {
                "extra_type": meta.get('extra_type', 'Sample'),
                "original": os.path.splitext(os.path.basename(file_path))[0],
                "parent": "Parent"
            }

            tmpl = extra_template
            if parent_path:
                parent_abs = os.path.abspath(os.path.join(directory, parent_path))
                
                # 1. Try to get parent variables from model
                res = parent_models.get(parent_abs)
                if not res:
                    # Fallback: try basename search in parent_models
                    p_base = os.path.basename(parent_path)
                    for m_path, m_val in parent_models.items():
                        if os.path.basename(m_path) == p_base:
                            res = m_val
                            break

                # Default 'parent' to the basename of the parent file
                extra_vars['parent'] = os.path.splitext(os.path.basename(parent_path))[0]

                # Self-healing: If parent name is generic, try to parse the extra's filename
                if extra_vars['parent'].lower() in ['sample', 'trailer', 'extra', 'parent']:
                    try:
                        from metadata.video_metadata import get_video_metadata
                        guessed = get_video_metadata(file_path)
                        if guessed and guessed.get('details'):
                            extra_vars['parent'] = guessed['details'].get('title') or extra_vars['parent']
                    except: pass

                if res:
                    parent_model, s_str, e_str = res
                    if parent_model.file_type == "movie":
                        tmpl = movie_extra_template or extra_template
                        extra_vars.update(parent_model.to_template_dict())
                        extra_vars['parent'] = parent_model.title
                        extra_vars['title'] = parent_model.title
                        extra_vars['year'] = parent_model.year
                    else:
                        tmpl = episode_extra_template or extra_template
                        extra_vars.update(parent_model.to_template_dict(s_str, e_str))
                        extra_vars['parent'] = parent_model.episode_title
                        extra_vars['title'] = parent_model.episode_title
                        extra_vars['series'] = parent_model.series_title
            
            try:
                new_filename = tmpl.format(**extra_vars)
            except Exception as e:
                logger.error(f"Extra template error: {e}")
                # Ultimate fallback: Use original name if parent is unknown
                new_filename = f"{extra_vars['original']} - {extra_vars['extra_type']}"

            name_without_ext = format_filename(new_filename, filename_case, separator)
            new_filename = name_without_ext + file_extension
            
            new_file_path = os.path.join(directory, new_filename)
            results.append(RenamingTask(old_path=file_path, new_filename=new_filename, new_path=new_file_path, status="pending"))

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
