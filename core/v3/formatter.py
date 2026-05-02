import re
import os

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

    def generate_name(self, file_id, template, casing="Original", separator=" ", custom_variable=""):
        """
        Generates the final formatted file name for a given file_id.
        Handles both Movie and TV Episode files based on their database link.
        """
        # Fetch file and media info
        file_data = self.db.get_file_by_id(file_id)
        if not file_data:
            return None
            
        # If it's a child file (extra/sub/audio), use the parent's API data
        target_file_id = file_data.get('parent_file_id') or file_id
            
        links = self.db.get_links_for_file(target_file_id)
        if not links:
            return None # Not matched yet
            
        # For now, we take the primary link (first one). 
        # Multi-episode formatting will be handled as an upgrade later.
        primary_link = links[0]

        with self.db._get_connection() as conn:
            media_item = conn.execute("SELECT * FROM media_items WHERE id = ?", (primary_link['media_item_id'],)).fetchone()
        
        if not media_item:
            return None

        # Build context dictionary for tags
        context = self._build_context(file_data, dict(media_item), custom_variable)
        
        # Add ParentName if this is a child file
        if file_data.get('parent_file_id'):
            # Generate the parent's name using the same base template
            parent_name = self.generate_name(file_data['parent_file_id'], template, casing, separator, custom_variable)
            context['ParentName'] = parent_name if parent_name else ""
        else:
            context['ParentName'] = ""
            
        # Replace tags in template
        formatted_name = template
        for tag, value in context.items():
            # Only replace if the value exists
            if value:
                formatted_name = formatted_name.replace(f"{{{tag}}}", str(value))
            else:
                formatted_name = formatted_name.replace(f"{{{tag}}}", "")

        # Clean up empty brackets and double spaces caused by missing variables
        formatted_name = self._cleanup_empty_tags(formatted_name)

        # Apply casing
        formatted_name = self._apply_casing(formatted_name, casing)

        # Apply separator smartly (Scene-style if not space)
        formatted_name = self._apply_separator(formatted_name, separator)

        return formatted_name

    def generate_full_path(self, file_id, settings):
        """
        Generates the absolute target path (Folder + File Name) for a file based on settings.
        """
        import os
        file_data = self.db.get_file_by_id(file_id)
        if not file_data:
            return None
            
        category = file_data.get('category')
        is_extra = category != 'video'
        
        # Get target ID for fetching metadata (parent if extra)
        target_file_id = file_data.get('parent_file_id') or file_id
        
        links = self.db.get_links_for_file(target_file_id)
        if not links:
            return None
        primary_link = links[0]
        
        with self.db._get_connection() as conn:
            media_item = conn.execute("SELECT * FROM media_items WHERE id = ?", (primary_link['media_item_id'],)).fetchone()
            
        if not media_item:
            return None
            
        media_type = media_item['media_type']
        
        # 1. Generate the base file name
        if is_extra:
            template = settings.movie_extra_template if media_type == 'movie' else settings.episode_extra_template
        else:
            template = settings.movie_template if media_type == 'movie' else settings.episode_template
            
        file_name = self.generate_name(file_id, template, settings.filename_case, settings.separator, settings.custom_variable)
        if not file_name:
            return None
            
        # Extension
        ext = file_data.get('extension', '')
        
        # 2. Build Directory Structure
        base_dir = ""
        if media_type == 'movie':
            base_dir = settings.target_dir_movies or os.path.dirname(file_data['current_path'])
        else:
            base_dir = settings.target_dir_shows or os.path.dirname(file_data['current_path'])
            
        # Prepare context for folder templates
        context = self._build_context(file_data, dict(media_item), settings.custom_variable)
        
        folders = []
        
        if media_type == 'movie':
            if settings.create_movie_folder:
                folder_name = settings.movie_folder_template
                for tag, val in context.items():
                    folder_name = folder_name.replace(f"{{{tag}}}", str(val))
                folders.append(self._cleanup_empty_tags(folder_name))
        elif media_type == 'tv':
            if settings.create_show_folder:
                folder_name = settings.show_folder_template
                for tag, val in context.items():
                    folder_name = folder_name.replace(f"{{{tag}}}", str(val))
                folders.append(self._cleanup_empty_tags(folder_name))
                
            if settings.create_season_folder:
                folder_name = settings.season_folder_template
                for tag, val in context.items():
                    folder_name = folder_name.replace(f"{{{tag}}}", str(val))
                folders.append(self._cleanup_empty_tags(folder_name))
                
            if settings.create_episode_folder:
                folder_name = settings.episode_folder_template
                for tag, val in context.items():
                    folder_name = folder_name.replace(f"{{{tag}}}", str(val))
                folders.append(self._cleanup_empty_tags(folder_name))
                
        # 3. Extras Subfolder
        if is_extra and settings.extras_folder_mode != "none":
            if settings.extras_folder_mode == "single":
                folders.append(settings.extras_folder_name)
            elif settings.extras_folder_mode == "categorized":
                folders.append(context.get("ExtraCategory", "Extras"))
                
        # 4. Combine
        target_dir = os.path.join(base_dir, *folders) if folders else base_dir
        
        return os.path.join(target_dir, f"{file_name}{ext}")

    def _build_context(self, file_data, media_item, custom_variable=""):
        """Constructs the dictionary of variables available for the template."""
        context = {
            # Base API Data
            "Title": media_item.get("title", ""),
            "Year": media_item.get("year", ""),
            "TMDB_ID": f"tmdb-{media_item.get('tmdb_id')}" if media_item.get("tmdb_id") else "",
            "IMDB_ID": media_item.get("imdb_id", ""),
            
            # Custom User Variable
            "Custom": custom_variable,
            
            # Technical Data
            "Resolution": self._map_resolution(file_data.get("resolution", "")),
            "VideoCodec": self._map_video_codec(file_data.get("video_codec", "")),
            "AudioCodec": self._map_audio_codec(file_data.get("audio_codec", "")),
            "AudioChannels": self._map_audio_channels(file_data.get("audio_channels", "")),
            "HDR": file_data.get("hdr_type", "") if file_data.get("hdr_type") != "SDR" else "",
            "BitDepth": f"{file_data.get('bit_depth')}bit" if file_data.get("bit_depth") else "",
            "Framerate": file_data.get("framerate", ""),
            
            # Extras / Companions
            "ExtraCategory": (file_data.get("sub_category") or file_data.get("category", "")).capitalize() if file_data.get("category") not in ("video", None) else "",
            "Original": os.path.splitext(file_data.get("file_name", ""))[0],
            "Language": (file_data.get("language") or "").upper(),
        }

        # TV Show specific data
        if media_item.get("media_type") == "tv":
            context["ShowTitle"] = context["Title"]
            context["Title"] = "" # Clear standard title so people don't mix them up
            
            # Get episode details
            with self.db._get_connection() as conn:
                ep = conn.execute(
                    "SELECT * FROM tv_episodes WHERE media_item_id = ? AND season_number = ? AND episode_number = ?", 
                    (media_item['id'], file_data.get('fn_season', 1), file_data.get('fn_episode', '1'))
                ).fetchone()
                
            if ep:
                context["Season"] = f"S{int(ep['season_number']):02d}"
                context["Episode"] = f"E{int(ep['episode_number']):02d}"
                context["EpisodeTitle"] = ep["name"]
            else:
                # Fallback to parsed numbers if not found in db
                season = file_data.get("fn_season") or file_data.get("fd_season") or 1
                episode = file_data.get("fn_episode") or file_data.get("fd_episode") or "1"
                context["Season"] = f"S{int(season):02d}"
                context["Episode"] = f"E{int(episode):02d}"
                context["EpisodeTitle"] = ""
        
        return context

    def _cleanup_empty_tags(self, text):
        """Cleans up leftover formatting when variables are empty."""
        # Remove empty brackets like [] or () or {}
        text = re.sub(r'\[\s*\]', '', text)
        text = re.sub(r'\(\s*\)', '', text)
        text = re.sub(r'\{\s*\}', '', text)
        
        # Fix dangling hyphens (e.g., "Movie - .mkv" -> "Movie .mkv")
        text = re.sub(r'\s+-\s+$', '', text)
        text = re.sub(r'^\s+-\s+', '', text)
        text = re.sub(r'\s+-\s+(?=\.)', '', text) # " - ." to "" before extension
        
        # Clean double spaces
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    def _apply_casing(self, text, casing):
        if casing == "Title":
            return text.title()
        elif casing == "Lower":
            return text.lower()
        elif casing == "Upper":
            return text.upper()
        # "Original" or unrecognized leaves it as is
        return text

    def _apply_separator(self, text, separator):
        sep_map = {
            "space": " ",
            "dot": ".",
            "dash": "-",
            "underscore": "_",
            "none": ""
        }
        # If it's already a single char like ".", use it. Otherwise map it.
        separator = sep_map.get(separator.lower(), separator) if separator else " "
        
        if separator == " " or not separator:
            return text
            
        # If user wants Scene-style (dot or underscore), we usually remove brackets
        # "The Matrix (1999) [1080p x264]" -> "The.Matrix.1999.1080p.x264"
        if separator in [".", "_"]:
            # Remove brackets, parentheses, curly braces
            text = re.sub(r'[\[\]\(\)\{\}]', '', text)
            # Remove dashes if they are surrounded by spaces, or replace them with separator
            text = re.sub(r'\s+-\s+', separator, text)
            
        # Replace all spaces with the chosen separator
        text = text.replace(" ", separator)
        
        # Clean up any duplicate separators (e.g., ".." -> ".")
        escaped_sep = re.escape(separator)
        text = re.sub(f'{escaped_sep}{{2,}}', separator, text)
        
        # Remove separator from the very end or beginning
        text = text.strip(separator)
        
        return text

    # --- MAPPING HELPERS ---

    def _map_resolution(self, res_str):
        if not res_str or "x" not in res_str:
            return res_str
        try:
            width, height = map(int, res_str.split("x"))
            if width >= 3800:
                return "4K"
            # Find closest standard height
            for std_h, name in self.RESOLUTION_MAP.items():
                if abs(height - std_h) <= 50: # small threshold for weird crops
                    return name
            return f"{height}p" # Fallback to raw height
        except Exception:
            return res_str

    def _map_video_codec(self, codec):
        if not codec: return ""
        codec = codec.upper()
        return self.VIDEO_CODEC_MAP.get(codec, codec)

    def _map_audio_codec(self, codec):
        if not codec: return ""
        codec = codec.upper()
        return self.AUDIO_CODEC_MAP.get(codec, codec)

    def _map_audio_channels(self, channels):
        if not channels: return ""
        return self.AUDIO_CHANNELS_MAP.get(str(channels), str(channels))
