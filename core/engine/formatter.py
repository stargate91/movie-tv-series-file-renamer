import re
import os
import json

class Formatter:
    """
    v3.0 Formatter: Generates final file names based on user templates,
    metadata from the database, and mapping rules (codecs, resolutions).
    """

    # Mappings for standardizing technical data
    RESOLUTION_MAP = {
        # Using height (or width for 4K) to determine standard names
        2160: "4K",
        1080: "1080p",
        720: "720p",
        480: "480p",
        576: "576p"
    }

    VIDEO_CODEC_MAP = {
        "H264": "x264",
        "AVC": "x264",
        "HEVC": "x265",
        "H265": "x265",
        "AV1": "AV1",
        "VP9": "VP9",
        "MPEG4": "XviD"
    }

    AUDIO_CODEC_MAP = {
        "AC-3": "AC3",
        "E-AC-3": "EAC3",
        "DCA": "DTS",
        "TRUEHD": "TrueHD",
        "FLAC": "FLAC",
        "AAC": "AAC",
        "MP3": "MP3"
    }

    AUDIO_CHANNELS_MAP = {
        "1": "1.0",
        "2": "2.0",
        "stereo": "2.0",
        "6": "5.1",
        "5.1(side)": "5.1",
        "8": "7.1",
        "7.1(wide)": "7.1"
    }

    def __init__(self, db):
        self.db = db

    def generate_name(self, file_id, settings):
        """
        Generates the final formatted file name for a given file_id.
        Handles multi-episode and multi-match files by merging metadata.
        """
        # Fetch file and media info
        row = self.db.get_file_by_id(file_id)
        if not row:
            return None
        file_data = dict(row)
            
        # Get target ID for fetching metadata (parent if extra)
        target_file_id = file_data.get('parent_file_id') or file_id
            
        links = self.db.get_links_for_file(target_file_id)
        if not links:
            return None # Not matched yet
            
        # Determine media_type from the DB
        with self.db._get_connection() as conn:
            m_row = conn.execute("SELECT media_type FROM media_items WHERE id = ?", (links[0]['media_item_id'],)).fetchone()
            
        if not m_row: return None
        media_type = m_row['media_type']

        # Determine the correct template for THIS specific file
        category = file_data.get('category')
        is_extra = category != 'video'
        
        if is_extra:
            if category == 'extra': template = settings.template_extra_video
            elif category == 'subtitle': template = settings.template_extra_subtitle
            elif category == 'audio': template = settings.template_extra_audio
            elif category == 'image': template = settings.template_extra_image
            elif category == 'metadata': template = settings.template_extra_metadata
            else: template = "{ParentName} - {ExtraCategory}"
        else:
            template = settings.movie_template if media_type == 'movie' else settings.episode_template

        # Build context dictionary for tags (handles multiple links)
        context = self._build_context(file_data, links, settings.custom_variable)
        
        # Add ParentName if this is a child file
        if file_data.get('parent_file_id'):
            # Generate the parent's name using its correct template recursively
            parent_name = self.generate_name(file_data['parent_file_id'], settings)
            context['ParentName'] = parent_name if parent_name else ""
        else:
            context['ParentName'] = ""
            
        # Replace tags in template
        formatted_name = template
        c_low = settings.filename_case.lower() if settings.filename_case else "none"
        
        # Tags that should be protected from Title Case mangling
        protected_tags = {"Language", "Resolution", "VideoCodec", "AudioCodec", 
                          "ParentName", "HDR", "BitDepth", "TMDB_ID", "IMDB_ID",
                          "SeriesResolution", "SeasonResolution", "Original"}
                          
        for tag, value in context.items():
            if not value:
                formatted_name = formatted_name.replace(f"{{{tag}}}", "")
                continue
                
            val_str = str(value)
            
            if c_low == "title" and tag not in protected_tags:
                val_str = val_str.title()
                
            formatted_name = formatted_name.replace(f"{{{tag}}}", val_str)

        # Clean up empty brackets and double spaces
        formatted_name = self._cleanup_empty_tags(formatted_name)
        
        # Apply global casing for lower/upper (Title case is handled per-tag)
        if c_low == "lower":
            formatted_name = formatted_name.lower()
        elif c_low == "upper":
            formatted_name = formatted_name.upper()
            
        formatted_name = self._apply_separator(formatted_name, settings.separator)
        formatted_name = self._sanitize_filename(formatted_name)

        return formatted_name

    def _build_context(self, file_data, links, custom_variable=""):
        """Constructs the dictionary of variables, merging data from multiple links if needed."""
        context = {
            # Technical Data (Always same for all links of a file)
            "Resolution": self._map_resolution(file_data.get("resolution", "")),
            "VideoCodec": self._map_video_codec(file_data.get("video_codec", "")),
            "AudioCodec": self._map_audio_codec(file_data.get("audio_codec", "")),
            "AudioChannels": self._map_audio_channels(file_data.get("audio_channels", "")),
            "HDR": file_data.get("hdr_type", "") if file_data.get("hdr_type") != "SDR" else "",
            "BitDepth": f"{file_data.get('bit_depth')}bit" if file_data.get("bit_depth") else "",
            "Framerate": file_data.get("framerate", ""),
            "Original": os.path.splitext(file_data.get("file_name", ""))[0],
            "Language": (file_data.get("language") or "").upper() if file_data.get("category") != "video" else "",
            "ExtraCategory": (file_data.get("sub_category") or file_data.get("category", "")).capitalize() if file_data.get("category") not in ("video", None) else "",
            "Custom": custom_variable,
            "VideoBitrate": f"{file_data['video_bitrate'] // 1000}kbps" if file_data.get('video_bitrate') else "",
            "ReleaseDate": "", # Will be filled from media item
            "Edition": file_data.get("edition", ""),
        }

        titles = []
        years = []
        show_titles = []
        seasons = []
        episodes = []
        ep_titles = []
        tmdb_ids = []
        imdb_ids = []

        with self.db._get_connection() as conn:
            for link in links:
                # 1. Fetch Media Item
                row = conn.execute("SELECT * FROM media_items WHERE id = ?", (link['media_item_id'],)).fetchone()
                if not row: continue
                media = dict(row)
                
                titles.append(media['title'])
                if media['year']: years.append(str(media['year']))
                if media['tmdb_id']: tmdb_ids.append(f"tmdb-{media['tmdb_id']}")
                if media['imdb_id']: imdb_ids.append(media['imdb_id'])
                
                # Global Media Info (Tags)
                context["Director"] = media.get('director', "")
                context["Cast"] = media.get('cast', "")
                context["RatingTmdb"] = media.get('rating_tmdb', "")
                context["RatingImdb"] = media.get('rating_imdb', "")
                context["RatingRotten"] = media.get('rating_rotten', "")
                context["RatingMetacritic"] = media.get('rating_metacritic', "")
                context["Budget"] = f"${media['budget']:,}" if media.get('budget') else ""
                context["Revenue"] = f"${media['revenue']:,}" if media.get('revenue') else ""
                context["Runtime"] = f"{media['runtime']} min" if media.get('runtime') else ""
                context["Genres"] = media.get('genres', "")
                context["Tagline"] = media.get('tagline', "")
                context["Popularity"] = media.get('popularity', "")
                context["OriginalTitle"] = media.get('original_title', "")
                context["SeriesOriginalTitle"] = media.get('original_title', "") # Alias
                context["OriginalLanguage"] = (media.get('original_language') or "").upper()
                context["Languages"] = media.get('languages', "")
                context["ReleaseDate"] = media.get('release_date') or media.get('first_air_date', "")
                
                # --- Advanced Series Tags ---
                if media['media_type'] == 'tv':
                    context["SeriesTitle"] = media['title']
                    context["SeriesRating"] = media.get('rating_imdb') or media.get('rating_tmdb', "")
                    context["EpisodeCount"] = media.get('number_of_episodes', "")
                    context["SeasonCount"] = media.get('number_of_seasons', "")
                    
                    # Year Extraction
                    f_year = ""
                    l_year = ""
                    if media.get('first_air_date'):
                        f_year = media['first_air_date'].split("-")[0]
                    if media.get('last_air_date'):
                        l_year = media['last_air_date'].split("-")[0]
                        
                    context["FirstAirYear"] = f_year
                    context["LastAirYear"] = l_year
                    
                    # Year Range Logic: 2014-2018 or 2014-
                    status = (media.get('status') or "").lower()
                    if status == "ended" and f_year and l_year:
                        context["YearRange"] = f"{f_year}-{l_year}"
                    elif f_year:
                        context["YearRange"] = f"{f_year}-"
                    else:
                        context["YearRange"] = ""
                        
                    # Series Level Resolution (Mixed / Range / Single)
                    context["SeriesResolution"] = self._get_series_resolution(media['id'])

                # 2. Fetch Episode if applicable
                if media['media_type'] == 'tv' and link['tv_episode_id']:
                    erow = conn.execute("SELECT * FROM tv_episodes WHERE id = ?", (link['tv_episode_id'],)).fetchone()
                    if erow:
                        ep = dict(erow)
                        show_titles.append(media['title'])
                        seasons.append(ep['season_number'])
                        episodes.append(ep['episode_number'])
                        if ep['name']: ep_titles.append(ep['name'])
                        
                        # Episode Specific Tags
                        context["EpisodeTMDB_ID"] = ep.get('tmdb_id', "")
                        context["EpisodeIMDB_ID"] = ep.get('imdb_id', "")
                        context["EpisodeRating"] = ep.get('vote_average', "")
                        context["EpisodeRatingImdb"] = ep.get('rating_imdb', "")
                        context["EpisodeRuntime"] = f"{ep['runtime']} min" if ep.get('runtime') else ""
                        context["EpisodeAirDate"] = ep.get('air_date', "")
                        if ep.get('air_date'):
                            try: context["EpisodeAirYear"] = ep['air_date'].split("-")[0]
                            except: context["EpisodeAirYear"] = ""
                        else:
                            context["EpisodeAirYear"] = ""
                elif media['media_type'] == 'tv':
                    # Linked to show but no specific episode? (e.g. season pack)
                    show_titles.append(media['title'])

        # Merge values (Remove duplicates while preserving order)
        def merge(items, sep=" & "):
            seen = set()
            unique = [str(x) for x in items if not (x in seen or seen.add(x))]
            return sep.join(unique)

        context["Title"] = merge(titles)
        context["Year"] = merge(years, sep=", ")
        context["TMDB_ID"] = merge(tmdb_ids)
        context["IMDB_ID"] = merge(imdb_ids)
        
        if show_titles:
            context["ShowTitle"] = merge(show_titles)
            context["Title"] = "" # Clear Title for TV shows to avoid redundancy
            
            # Fallback to parsed numbers if no specific episodes are linked in DB
            if not seasons:
                s_val = file_data.get("fn_season") or file_data.get("fd_season") or 1
                seasons = [s_val]
            if not episodes:
                e_val = file_data.get("fn_episode") or file_data.get("fd_episode") or 1
                # Handle case where e_val is already a list (from guessit)
                if isinstance(e_val, (list, tuple)): episodes = list(e_val)
                elif isinstance(e_val, str) and e_val.startswith('['):
                    import ast
                    try: episodes = ast.literal_eval(e_val)
                    except: episodes = [e_val]
                else: episodes = [e_val]

            context["Season"] = self._format_list(seasons, "S")
            context["Episode"] = self._format_list(episodes, "E")
            context["EpisodeTitle"] = merge(ep_titles)

        # 3. Extract Director and Cast from details_json (Pocket Library enrichment)
        context["Director"] = ""
        context["Cast"] = ""
        
        try:
            # We take the details from the first link's media item
            first_media_id = links[0]['media_item_id']
            with self.db._get_connection() as conn:
                m = conn.execute("SELECT details_json, media_type FROM media_items WHERE id = ?", (first_media_id,)).fetchone()
            
            if m and m['details_json']:
                details = json.loads(m['details_json'])
                
                # Director / Creator
                directors = []
                if m['media_type'] == 'movie':
                    # TMDB Movie Crew
                    crew = details.get('credits', {}).get('crew', [])
                    directors = [p['name'] for p in crew if p.get('job') == 'Director']
                else:
                    # TMDB TV Creators
                    creators = details.get('created_by', [])
                    directors = [p['name'] for p in creators]
                
                context["Director"] = ", ".join(directors[:2]) if directors else ""
                
                # Cast (Top 3)
                cast = details.get('credits', {}).get('cast', [])
                actors = [p['name'] for p in cast[:3]]
                context["Cast"] = ", ".join(actors) if actors else ""

                # --- Season Specific Metadata Enrichment ---
                if media['media_type'] == 'tv' and seasons:
                    # Get the first season number we're dealing with
                    s_num = seasons[0]
                    # Find this season in the TMDB seasons list
                    tmdb_seasons = details.get('seasons', [])
                    target_s = next((s for s in tmdb_seasons if s.get('season_number') == s_num), None)
                    
                    if target_s:
                        context["SeasonName"] = target_s.get('name', f"Season {s_num}")
                        context["SeasonEpisodeCount"] = target_s.get('episode_count', "")
                        s_air = target_s.get('air_date', "")
                        context["SeasonAirDate"] = s_air
                        context["SeasonAirYear"] = s_air.split("-")[0] if "-" in s_air else ""
                        context["SeasonResolution"] = self._get_series_resolution(media['id'], s_num)
        except:
            pass

        return context

    def _format_list(self, nums, prefix):
        """Formats a list of numbers: [1, 2] -> S01-S02."""
        if not nums: return ""
        seen = set()
        unique = sorted([int(x) for x in nums if not (x in seen or seen.add(x))])
        if len(unique) == 1:
            return f"{prefix}{unique[0]:02d}"
        return "-".join([f"{prefix}{x:02d}" for x in unique])

    def generate_full_path(self, file_id, settings):
        """
        Generates the absolute target path (Folder + File Name) for a file based on settings.
        """
        import os
        row = self.db.get_file_by_id(file_id)
        if not row:
            return None
        file_data = dict(row)
            
        category = file_data.get('category')
        is_extra = category != 'video'
        
        # Get target ID for fetching metadata (parent if extra)
        target_file_id = file_data.get('parent_file_id') or file_id
        
        links = self.db.get_links_for_file(target_file_id)
        if not links:
            return None
        with self.db._get_connection() as conn:
            m_row = conn.execute("SELECT * FROM media_items WHERE id = ?", (links[0]['media_item_id'],)).fetchone()
            
        if not m_row:
            return None
        media_item = dict(m_row)
            
        media_type = media_item['media_type']
        
        # 1. Generate the base file name
        file_name = self.generate_name(file_id, settings)
        if not file_name:
            return None
            
        # Extension
        ext = file_data.get('extension', '')
        
        # 2. Build Directory Structure
        if is_extra and file_data.get('parent_file_id'):
            # If it's an extra, we inherit the exact target directory of its parent video!
            parent_full_path = self.generate_full_path(file_data['parent_file_id'], settings)
            if not parent_full_path: return None
            
            base_dir = os.path.dirname(parent_full_path)
            folders = []
            
            # Prepare context for the Extra Category (Using ALL links)
            context = self._build_context(file_data, links, settings.custom_variable)
            
            # Extras Subfolder
            if settings.extras_folder_mode != "none":
                if settings.extras_folder_mode == "single":
                    folders.append(settings.extras_folder_name)
                elif settings.extras_folder_mode == "categorized":
                    folders.append(context.get("ExtraCategory", "Extras"))
                    
        else:
            # It's a video file, generate its directory structure
            base_dir = ""
            if settings.move_files and settings.base_target_path:
                base_dir = settings.base_target_path
                if settings.auto_organize_by_type:
                    sub = settings.movies_subfolder_name if media_type == 'movie' else settings.shows_subfolder_name
                    if sub:
                        base_dir = os.path.join(base_dir, sub)
            else:
                base_dir = os.path.dirname(file_data['current_path'])
                
            # Prepare context for folder templates (Using ALL links)
            context = self._build_context(file_data, links, settings.custom_variable)
            
            folders = []
            
            if media_type == 'movie':
                if settings.create_movie_folder:
                    folder_name = settings.movie_folder_template
                    for tag, val in context.items():
                        # Protect against None values
                        val_str = str(val) if val is not None else ""
                        folder_name = folder_name.replace(f"{{{tag}}}", val_str)
                    folders.append(self._cleanup_empty_tags(folder_name))
            elif media_type == 'tv':
                if settings.create_show_folder:
                    folder_name = settings.show_folder_template
                    for tag, val in context.items():
                        val_str = str(val) if val is not None else ""
                        folder_name = folder_name.replace(f"{{{tag}}}", val_str)
                    folders.append(self._cleanup_empty_tags(folder_name))
                    
                if settings.create_season_folder:
                    folder_name = settings.season_folder_template
                    for tag, val in context.items():
                        val_str = str(val) if val is not None else ""
                        folder_name = folder_name.replace(f"{{{tag}}}", val_str)
                    folders.append(self._cleanup_empty_tags(folder_name))
                    
                if settings.create_episode_folder:
                    folder_name = settings.episode_folder_template
                    for tag, val in context.items():
                        val_str = str(val) if val is not None else ""
                        folder_name = folder_name.replace(f"{{{tag}}}", val_str)
                    folders.append(self._cleanup_empty_tags(folder_name))
        
        # 3b. Sanitize all folder names (remove illegal characters)
        folders = [self._sanitize_filename(f) for f in folders]
                
        # 4. Combine
        target_dir = os.path.join(base_dir, *folders) if folders else base_dir
        
        full_path = os.path.join(target_dir, f"{file_name}{ext}")
        
        # 5. Path length safety (Windows MAX_PATH = 260)
        MAX_PATH = 260
        if len(full_path) > MAX_PATH:
            # First try: truncate only the filename
            overhead = len(target_dir) + len(ext) + 2
            max_name_len = MAX_PATH - overhead
            if max_name_len > 20:
                file_name = file_name[:max_name_len].rstrip('. ')
                full_path = os.path.join(target_dir, f"{file_name}{ext}")
            
            # Second try: if still too long, truncate folder names too
            if len(full_path) > MAX_PATH and folders:
                MAX_FOLDER_NAME = 60
                truncated_folders = [f[:MAX_FOLDER_NAME].rstrip('. ') if len(f) > MAX_FOLDER_NAME else f for f in folders]
                target_dir = os.path.join(base_dir, *truncated_folders)
                overhead = len(target_dir) + len(ext) + 2
                max_name_len = MAX_PATH - overhead
                if max_name_len > 20:
                    file_name = file_name[:max_name_len].rstrip('. ')
                full_path = os.path.join(target_dir, f"{file_name}{ext}")
        
        return full_path

    def _cleanup_empty_tags(self, text):
        """Cleans up leftover formatting when variables are empty."""
        import re
        # 1. Remove any leftover unknown/typo tags like {Yera}, {Resoluton}
        text = re.sub(r'\{[^}]+\}', '', text)
        
        # 2. Remove empty brackets like [] or () or {}
        text = re.sub(r'\[\s*\]', '', text)
        text = re.sub(r'\(\s*\)', '', text)
        text = re.sub(r'\{\s*\}', '', text)
        
        # 3. Collapse multiple hyphens/dashes with spaces: " -  - " -> " - "
        # This handles cases where {Season}{Episode} are missing between dashes
        text = re.sub(r'(\s*-\s*){2,}', ' - ', text)
        
        # 4. Fix dangling hyphens at start/end
        text = re.sub(r'\s+-\s+$', '', text)
        text = re.sub(r'^\s+-\s+', '', text)
        text = re.sub(r'\s+-\s+(?=\.)', '', text) # " - ." to "" before extension
        
        # 5. Clean double spaces and trim
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def _sanitize_filename(self, text):
        """Removes characters that are illegal in Windows file/folder names."""
        # Windows forbidden: \ / : * ? " < > |
        # We keep / and \ out since those are path separators handled elsewhere
        illegal_chars = ':*?"<>|'
        for ch in illegal_chars:
            text = text.replace(ch, '')
        # Clean up any double spaces created by removal
        import re
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def _apply_casing(self, text, casing):
        if not casing or casing.lower() in ("none", "original"):
            return text
        
        c_low = casing.lower()
        if c_low == "title":
            return text.title()
        elif c_low == "lower":
            return text.lower()
        elif c_low == "upper":
            return text.upper()
        return text

    def _apply_separator(self, text, separator):
        import re
        sep_map = {
            "space": " ", "dot": ".", "dash": "-", "underscore": "_", "none": ""
        }
        separator = sep_map.get(separator.lower(), separator) if separator else " "
        
        if separator == " " or not separator:
            return text
            
        if separator in [".", "_"]:
            text = re.sub(r'[\[\]\(\)\{\}]', '', text)
            text = re.sub(r'\s+-\s+', separator, text)
            
        text = text.replace(" ", separator)
        escaped_sep = re.escape(separator)
        text = re.sub(f'{escaped_sep}{{2,}}', separator, text)
        return text.strip(separator)

    def _map_resolution(self, res_str):
        if not res_str or "x" not in res_str:
            return res_str
        try:
            width, height = map(int, res_str.split("x"))
            if width >= 3800: return "4K"
            for std_h, name in self.RESOLUTION_MAP.items():
                if abs(height - std_h) <= 50: return name
            return f"{height}p"
        except Exception:
            return res_str

    def _map_video_codec(self, codec):
        if not codec: return ""
        return self.VIDEO_CODEC_MAP.get(codec.upper(), codec)

    def _map_audio_codec(self, codec):
        if not codec: return ""
        return self.AUDIO_CODEC_MAP.get(codec.upper(), codec)

    def _map_audio_channels(self, channels):
        if not channels: return ""
        return self.AUDIO_CHANNELS_MAP.get(str(channels), str(channels))

    def _get_series_resolution(self, media_item_id, season_number=None):
        """Calculates the overall resolution for a TV series (or specific season) based on its files."""
        try:
            with self.db._get_connection() as conn:
                # Get resolutions from all files linked to this media item
                if season_number is not None:
                    query = """
                        SELECT f.resolution 
                        FROM files f
                        JOIN links l ON f.id = l.file_id
                        JOIN tv_episodes e ON l.tv_episode_id = e.id
                        WHERE l.media_item_id = ? AND e.season_number = ?
                    """
                    rows = conn.execute(query, (media_item_id, season_number)).fetchall()
                else:
                    query = """
                        SELECT f.resolution 
                        FROM files f
                        JOIN links l ON f.id = l.file_id
                        WHERE l.media_item_id = ?
                    """
                    rows = conn.execute(query, (media_item_id,)).fetchall()
                
            resolutions = set()
            for r in rows:
                if r['resolution']:
                    mapped = self._map_resolution(r['resolution'])
                    if mapped: resolutions.add(mapped)
                    
            if not resolutions: return ""
            
            # Sort order for common resolutions
            res_order = {"4K": 4, "1080p": 3, "720p": 2, "576p": 1, "480p": 0}
            sorted_res = sorted(list(resolutions), key=lambda x: res_order.get(x, -1))
            
            if len(sorted_res) == 1: 
                return sorted_res[0]
            if len(sorted_res) == 2:
                return f"{sorted_res[0]}-{sorted_res[1]}"
                
            return "Mixed"
        except:
            return "Mixed"
